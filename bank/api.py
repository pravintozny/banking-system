"""Minimal JSON HTTP API (stdlib only).

Run: python -m bank.api [--db bank.sqlite3] [--port 8000]
"""
import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import db
from .accounts import AccountService
from .customers import CustomerService
from .errors import BankError, NotFoundError, ValidationError
from .transactions import TransactionService


class App:
    def __init__(self, conn):
        self.customers = CustomerService(conn)
        self.accounts = AccountService(conn)
        self.transactions = TransactionService(conn)

    def dispatch(self, method, path, query, body):
        c, a, t = self.customers, self.accounts, self.transactions
        routes = [
            ("POST", r"/customers", lambda m: (201, c.register(**_kw(body, "first_name", "last_name", "date_of_birth", "email", "phone", opt=("address",))))),
            ("GET", r"/customers/(\d+)", lambda m: (200, c.get(int(m[1])))),
            ("PATCH", r"/customers/(\d+)", lambda m: (200, c.update_contact(int(m[1]), **_kw(body, opt=("email", "phone", "address"))))),
            ("PUT", r"/customers/(\d+)/kyc", lambda m: (200, c.set_kyc_status(int(m[1]), body.get("kyc_status")))),
            ("POST", r"/customers/(\d+)/documents", lambda m: (201, c.add_document(int(m[1]), **_kw(body, "doc_type", "doc_number")))),
            ("GET", r"/customers/(\d+)/documents", lambda m: (200, c.list_documents(int(m[1])))),
            ("POST", r"/customers/(\d+)/accounts", lambda m: (201, a.open_account(int(m[1]), body.get("account_type")))),
            ("GET", r"/customers/(\d+)/accounts", lambda m: (200, a.list_for_customer(int(m[1])))),
            ("GET", r"/accounts/(\d+)", lambda m: (200, a.get(int(m[1])))),
            ("PUT", r"/accounts/(\d+)/status", lambda m: (200, a.set_status(int(m[1]), body.get("status")))),
            ("POST", r"/accounts/(\d+)/deposit", lambda m: (201, t.deposit(int(m[1]), body.get("amount"), body.get("description", "")))),
            ("POST", r"/accounts/(\d+)/withdraw", lambda m: (201, t.withdraw(int(m[1]), body.get("amount"), body.get("description", "")))),
            ("GET", r"/accounts/(\d+)/transactions", lambda m: (200, t.history(int(m[1]), query.get("limit", 100), query.get("offset", 0)))),
            ("POST", r"/transfers", lambda m: (201, t.transfer(_int(body, "from_account_id"), _int(body, "to_account_id"), body.get("amount"), body.get("description", "")))),
            ("GET", r"/transactions/(\w+)", lambda m: (200, t.get_by_reference(m[1]))),
            ("POST", r"/transactions/(\w+)/reverse", lambda m: (201, t.reverse(t.get_by_reference(m[1])["id"], body.get("reason", "")))),
        ]
        for meth, pattern, handler in routes:
            if meth == method:
                m = re.fullmatch(pattern, path)
                if m:
                    return handler(m)
        raise NotFoundError("route not found")


def _kw(body, *required, opt=()):
    missing = [k for k in required if k not in body]
    if missing:
        raise ValidationError(f"missing fields: {', '.join(missing)}")
    return {k: body[k] for k in (*required, *opt) if k in body}


def _int(body, key):
    try:
        return int(body[key])
    except (KeyError, TypeError, ValueError):
        raise ValidationError(f"{key} must be an integer")


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def _handle(self):
            url = urlparse(self.path)
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw or b"{}")
                if not isinstance(body, dict):
                    raise ValueError
            except (ValueError, json.JSONDecodeError):
                return self._send(422, {"error": "body must be a JSON object"})
            try:
                status, payload = app.dispatch(self.command, url.path.rstrip("/") or "/", query, body)
            except BankError as e:
                status, payload = e.status, {"error": str(e)}
            self._send(status, payload)

        do_GET = do_POST = do_PUT = do_PATCH = _handle

        def _send(self, status, payload):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass
    return Handler


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="bank.sqlite3")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()
    app = App(db.connect(args.db))
    print(f"Listening on http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(app)).serve_forever()


if __name__ == "__main__":
    main()
