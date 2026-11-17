import secrets

from .accounts import present as present_account
from .errors import ConflictError, NotFoundError, ValidationError
from .money import from_cents, to_cents


def _present(row):
    d = dict(row)
    d["amount"] = from_cents(d.pop("amount_cents"))
    return d


class TransactionService:
    def __init__(self, conn):
        self.conn = conn

    # -- helpers ---------------------------------------------------------
    def _reference(self):
        return "TXN" + secrets.token_hex(8).upper()

    def _account(self, account_id):
        r = self.conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        if not r:
            raise NotFoundError(f"account {account_id} not found")
        return r

    def _require_active(self, acct):
        if acct["status"] != "ACTIVE":
            raise ConflictError(f"account {acct['account_number']} is {acct['status']}")

    def _adjust(self, account_id, delta_cents):
        cur = self.conn.execute(
            "UPDATE accounts SET balance_cents = balance_cents + ? "
            "WHERE id=? AND balance_cents + ? >= 0",
            (delta_cents, account_id, delta_cents),
        )
        if cur.rowcount != 1:
            raise ConflictError("insufficient funds")

    def _insert(self, type_, cents, from_id, to_id, description="", reverses_id=None):
        cur = self.conn.execute(
            "INSERT INTO transactions(reference,type,amount_cents,from_account_id,"
            "to_account_id,reverses_id,description) VALUES (?,?,?,?,?,?,?)",
            (self._reference(), type_, cents, from_id, to_id, reverses_id, description),
        )
        return cur.lastrowid

    def _run(self, fn):
        """Execute fn atomically; roll back on any failure."""
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            tx_id = fn()
            self.conn.commit()
            return self.get(tx_id)
        except BaseException:
            self.conn.rollback()
            raise

    # -- operations ------------------------------------------------------
    def deposit(self, account_id, amount, description=""):
        cents = to_cents(amount)

        def work():
            self._require_active(self._account(account_id))
            self._adjust(account_id, cents)
            return self._insert("DEPOSIT", cents, None, account_id, description)
        return self._run(work)

    def withdraw(self, account_id, amount, description=""):
        cents = to_cents(amount)

        def work():
            self._require_active(self._account(account_id))
            self._adjust(account_id, -cents)
            return self._insert("WITHDRAWAL", cents, account_id, None, description)
        return self._run(work)

    def transfer(self, from_account_id, to_account_id, amount, description=""):
        cents = to_cents(amount)
        if from_account_id == to_account_id:
            raise ValidationError("cannot transfer to the same account")

        def work():
            self._require_active(self._account(from_account_id))
            self._require_active(self._account(to_account_id))
            self._adjust(from_account_id, -cents)
            self._adjust(to_account_id, cents)
            return self._insert("TRANSFER", cents, from_account_id, to_account_id, description)
        return self._run(work)

    def reverse(self, transaction_id, reason=""):
        """Reverse a COMPLETED deposit/withdrawal/transfer by posting an offsetting entry."""
        def work():
            r = self.conn.execute(
                "SELECT * FROM transactions WHERE id=?", (transaction_id,)).fetchone()
            if not r:
                raise NotFoundError("transaction not found")
            if r["type"] == "REVERSAL":
                raise ConflictError("a reversal cannot be reversed")
            if r["status"] != "COMPLETED":
                raise ConflictError("transaction already reversed")
            src, dst, cents = r["from_account_id"], r["to_account_id"], r["amount_cents"]
            # Money flows back: credit the original source, debit the original destination.
            if dst is not None:
                self._adjust(dst, -cents)
            if src is not None:
                self._adjust(src, cents)
            self.conn.execute(
                "UPDATE transactions SET status='REVERSED' WHERE id=?", (transaction_id,))
            return self._insert("REVERSAL", cents, dst, src, reason, reverses_id=transaction_id)
        return self._run(work)

    # -- queries ---------------------------------------------------------
    def get(self, transaction_id):
        r = self.conn.execute(
            "SELECT * FROM transactions WHERE id=?", (transaction_id,)).fetchone()
        if not r:
            raise NotFoundError("transaction not found")
        return _present(r)

    def get_by_reference(self, reference):
        r = self.conn.execute(
            "SELECT * FROM transactions WHERE reference=?", (reference,)).fetchone()
        if not r:
            raise NotFoundError("transaction not found")
        return _present(r)

    def history(self, account_id, limit=100, offset=0):
        self._account(account_id)
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        return [_present(r) for r in self.conn.execute(
            "SELECT * FROM transactions WHERE from_account_id=? OR to_account_id=? "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            (account_id, account_id, limit, offset))]
