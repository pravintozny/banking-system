import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError

from bank import db
from bank.accounts import AccountService, _luhn_check_digit
from bank.api import App, make_handler
from bank.customers import CustomerService
from bank.errors import ConflictError, NotFoundError, ValidationError
from bank.transactions import TransactionService


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect()
        self.cs = CustomerService(self.conn)
        self.acc = AccountService(self.conn)
        self.tx = TransactionService(self.conn)

    def customer(self, email="a@example.com", verified=True):
        c = self.cs.register("Ada", "Lovelace", "1990-01-01", email, "+1 555 123 4567")
        if verified:
            self.cs.add_document(c["id"], "passport", "P" + email)
            self.cs.set_kyc_status(c["id"], "VERIFIED")
        return c

    def account(self, c=None, type_="SAVINGS", funds=None):
        c = c or self.customer()
        a = self.acc.open_account(c["id"], type_)
        if funds:
            self.tx.deposit(a["id"], funds)
        return a


class CustomerTests(Base):
    def test_register_defaults_pending(self):
        c = self.customer(verified=False)
        self.assertEqual(c["kyc_status"], "PENDING")

    def test_validation(self):
        with self.assertRaises(ValidationError):
            self.cs.register("A", "B", "2020-01-01", "a@example.com", "+15551234567")
        with self.assertRaises(ValidationError):
            self.cs.register("A", "B", "1990-01-01", "bad", "+15551234567")
        with self.assertRaises(ValidationError):
            self.cs.register("A", "B", "1990-01-01", "a@example.com", "abc")

    def test_duplicate_email(self):
        self.customer()
        with self.assertRaises(ConflictError):
            self.customer()

    def test_update_contact(self):
        c = self.customer()
        u = self.cs.update_contact(c["id"], phone="+44 20 7946 0958", address="1 Road")
        self.assertEqual(u["address"], "1 Road")

    def test_kyc_requires_document(self):
        c = self.customer(verified=False)
        with self.assertRaises(ValidationError):
            self.cs.set_kyc_status(c["id"], "VERIFIED")

    def test_documents(self):
        c = self.customer(verified=False)
        self.cs.add_document(c["id"], "nid", "123")
        with self.assertRaises(ConflictError):
            self.cs.add_document(self.customer("b@example.com", False)["id"], "NID", "123")
        self.assertEqual(len(self.cs.list_documents(c["id"])), 1)


class AccountTests(Base):
    def test_requires_kyc(self):
        c = self.customer(verified=False)
        with self.assertRaises(ValidationError):
            self.acc.open_account(c["id"], "SAVINGS")

    def test_multiple_accounts_and_numbers(self):
        c = self.customer()
        a1 = self.acc.open_account(c["id"], "SAVINGS")
        a2 = self.acc.open_account(c["id"], "CURRENT")
        self.assertNotEqual(a1["account_number"], a2["account_number"])
        self.assertEqual(len(a1["account_number"]), 12)
        self.assertTrue(a1["account_number"].startswith("10"))
        self.assertTrue(a2["account_number"].startswith("20"))
        n = a1["account_number"]
        self.assertEqual(_luhn_check_digit(n[:-1]), n[-1])
        self.assertEqual(len(self.acc.list_for_customer(c["id"])), 2)
        self.assertEqual(a1["balance"], "0.00")

    def test_invalid_type(self):
        with self.assertRaises(ValidationError):
            self.acc.open_account(self.customer()["id"], "GOLD")

    def test_status_rules(self):
        a = self.account(funds="10.00")
        with self.assertRaises(ConflictError):
            self.acc.set_status(a["id"], "CLOSED")
        self.acc.set_status(a["id"], "FROZEN")
        with self.assertRaises(ConflictError):
            self.tx.deposit(a["id"], "1.00")
        self.acc.set_status(a["id"], "ACTIVE")
        self.tx.withdraw(a["id"], "10.00")
        self.assertEqual(self.acc.set_status(a["id"], "CLOSED")["status"], "CLOSED")
        with self.assertRaises(ConflictError):
            self.acc.set_status(a["id"], "ACTIVE")


class TransactionTests(Base):
    def test_deposit_withdraw(self):
        a = self.account()
        t = self.tx.deposit(a["id"], "100.50")
        self.assertTrue(t["reference"].startswith("TXN"))
        self.assertEqual(t["status"], "COMPLETED")
        self.tx.withdraw(a["id"], "40.25")
        self.assertEqual(self.acc.get(a["id"])["balance"], "60.25")

    def test_overdraw_rejected_and_atomic(self):
        a = self.account(funds="10.00")
        with self.assertRaises(ConflictError):
            self.tx.withdraw(a["id"], "10.01")
        self.assertEqual(self.acc.get(a["id"])["balance"], "10.00")
        self.assertEqual(len(self.tx.history(a["id"])), 1)

    def test_amount_validation(self):
        a = self.account()
        for bad in ("0", "-5", "abc", "1.001", "NaN", None):
            with self.assertRaises(ValidationError):
                self.tx.deposit(a["id"], bad)

    def test_transfer(self):
        a = self.account(funds="50.00")
        b = self.account(self.customer("b@example.com"), "CURRENT")
        t = self.tx.transfer(a["id"], b["id"], "20.00")
        self.assertEqual(self.acc.get(a["id"])["balance"], "30.00")
        self.assertEqual(self.acc.get(b["id"])["balance"], "20.00")
        self.assertEqual(self.tx.get_by_reference(t["reference"])["id"], t["id"])

    def test_transfer_failures_roll_back(self):
        a = self.account(funds="5.00")
        b = self.account(self.customer("b@example.com"))
        with self.assertRaises(ConflictError):
            self.tx.transfer(a["id"], b["id"], "6.00")
        with self.assertRaises(ValidationError):
            self.tx.transfer(a["id"], a["id"], "1.00")
        self.acc.set_status(b["id"], "FROZEN")
        with self.assertRaises(ConflictError):
            self.tx.transfer(a["id"], b["id"], "1.00")
        self.assertEqual(self.acc.get(a["id"])["balance"], "5.00")

    def test_history(self):
        a = self.account(funds="50.00")
        b = self.account(self.customer("b@example.com"))
        self.tx.transfer(a["id"], b["id"], "10.00")
        self.tx.withdraw(a["id"], "1.00")
        h = self.tx.history(a["id"])
        self.assertEqual([x["type"] for x in h], ["WITHDRAWAL", "TRANSFER", "DEPOSIT"])
        self.assertEqual(len(self.tx.history(b["id"])), 1)
        self.assertEqual(len(self.tx.history(a["id"], limit=1)), 1)
        with self.assertRaises(NotFoundError):
            self.tx.history(9999)

    def test_reverse_transfer(self):
        a = self.account(funds="50.00")
        b = self.account(self.customer("b@example.com"))
        t = self.tx.transfer(a["id"], b["id"], "20.00")
        r = self.tx.reverse(t["id"], "mistake")
        self.assertEqual(r["type"], "REVERSAL")
        self.assertEqual(r["reverses_id"], t["id"])
        self.assertEqual(self.tx.get(t["id"])["status"], "REVERSED")
        self.assertEqual(self.acc.get(a["id"])["balance"], "50.00")
        self.assertEqual(self.acc.get(b["id"])["balance"], "0.00")
        with self.assertRaises(ConflictError):
            self.tx.reverse(t["id"])
        with self.assertRaises(ConflictError):
            self.tx.reverse(r["id"])

    def test_reverse_deposit_and_withdrawal(self):
        a = self.account()
        d = self.tx.deposit(a["id"], "10.00")
        self.tx.reverse(d["id"])
        self.assertEqual(self.acc.get(a["id"])["balance"], "0.00")
        self.tx.deposit(a["id"], "10.00")
        w = self.tx.withdraw(a["id"], "4.00")
        self.tx.reverse(w["id"])
        self.assertEqual(self.acc.get(a["id"])["balance"], "10.00")

    def test_reverse_fails_when_funds_spent(self):
        a = self.account()
        d = self.tx.deposit(a["id"], "10.00")
        self.tx.withdraw(a["id"], "10.00")
        with self.assertRaises(ConflictError):
            self.tx.reverse(d["id"])
        self.assertEqual(self.tx.get(d["id"])["status"], "COMPLETED")


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(App(db.connect())))
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, method, path, body=None):
        req = urllib.request.Request(
            self.base + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r)
        except HTTPError as e:
            return e.code, json.load(e)

    def test_end_to_end(self):
        s, c = self.call("POST", "/customers", {
            "first_name": "Grace", "last_name": "Hopper", "date_of_birth": "1985-12-09",
            "email": "g@example.com", "phone": "+15551234567"})
        self.assertEqual(s, 201)
        cid = c["id"]
        self.assertEqual(self.call("POST", f"/customers/{cid}/accounts", {"account_type": "SAVINGS"})[0], 422)
        self.call("POST", f"/customers/{cid}/documents", {"doc_type": "PASSPORT", "doc_number": "X1"})
        self.assertEqual(self.call("PUT", f"/customers/{cid}/kyc", {"kyc_status": "VERIFIED"})[0], 200)
        s, a1 = self.call("POST", f"/customers/{cid}/accounts", {"account_type": "SAVINGS"})
        s, a2 = self.call("POST", f"/customers/{cid}/accounts", {"account_type": "CURRENT"})
        self.assertEqual(s, 201)
        self.call("POST", f"/accounts/{a1['id']}/deposit", {"amount": "100.00"})
        s, t = self.call("POST", "/transfers", {
            "from_account_id": a1["id"], "to_account_id": a2["id"], "amount": "25.00"})
        self.assertEqual(s, 201)
        self.assertEqual(self.call("GET", f"/accounts/{a2['id']}")[1]["balance"], "25.00")
        s, r = self.call("POST", f"/transactions/{t['reference']}/reverse", {"reason": "x"})
        self.assertEqual(s, 201)
        self.assertEqual(self.call("GET", f"/accounts/{a2['id']}")[1]["balance"], "0.00")
        s, h = self.call("GET", f"/accounts/{a1['id']}/transactions")
        self.assertEqual(len(h), 3)
        self.assertEqual(self.call("POST", f"/accounts/{a1['id']}/withdraw", {"amount": "999"})[0], 409)
        self.assertEqual(self.call("GET", "/nope")[0], 404)
        self.assertEqual(self.call("GET", "/accounts/999")[0], 404)


if __name__ == "__main__":
    unittest.main()
