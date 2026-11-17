import secrets

from .customers import CustomerService
from .errors import ConflictError, NotFoundError, ValidationError
from .money import from_cents

ACCOUNT_TYPES = ("SAVINGS", "CURRENT")
ACCOUNT_STATUSES = ("ACTIVE", "FROZEN", "CLOSED")
_PREFIX = {"SAVINGS": "10", "CURRENT": "20"}


def _luhn_check_digit(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return str((10 - total % 10) % 10)


def present(row):
    d = dict(row)
    d["balance"] = from_cents(d.pop("balance_cents"))
    return d


class AccountService:
    def __init__(self, conn):
        self.conn = conn
        self.customers = CustomerService(conn)

    def _generate_number(self, account_type):
        """12 digits: 2-digit type prefix + 9 random digits + Luhn check digit."""
        for _ in range(20):
            body = _PREFIX[account_type] + f"{secrets.randbelow(10**9):09d}"
            number = body + _luhn_check_digit(body)
            if not self.conn.execute(
                "SELECT 1 FROM accounts WHERE account_number=?", (number,)).fetchone():
                return number
        raise ConflictError("could not generate unique account number")

    def open_account(self, customer_id, account_type):
        customer = self.customers.get(customer_id)
        if account_type not in ACCOUNT_TYPES:
            raise ValidationError(f"account_type must be one of {ACCOUNT_TYPES}")
        if customer["kyc_status"] != "VERIFIED":
            raise ValidationError("customer KYC must be VERIFIED to open an account")
        number = self._generate_number(account_type)
        cur = self.conn.execute(
            "INSERT INTO accounts(account_number,customer_id,account_type) VALUES (?,?,?)",
            (number, customer_id, account_type),
        )
        self.conn.commit()
        return self.get(cur.lastrowid)

    def get(self, account_id):
        r = self.conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        if not r:
            raise NotFoundError("account not found")
        return present(r)

    def get_by_number(self, number):
        r = self.conn.execute(
            "SELECT * FROM accounts WHERE account_number=?", (number,)).fetchone()
        if not r:
            raise NotFoundError("account not found")
        return present(r)

    def list_for_customer(self, customer_id):
        self.customers.get(customer_id)
        return [present(r) for r in self.conn.execute(
            "SELECT * FROM accounts WHERE customer_id=? ORDER BY id", (customer_id,))]

    def set_status(self, account_id, status):
        if status not in ACCOUNT_STATUSES:
            raise ValidationError(f"status must be one of {ACCOUNT_STATUSES}")
        acct = self.get(account_id)
        if acct["status"] == "CLOSED":
            raise ConflictError("closed accounts cannot change status")
        if status == "CLOSED" and acct["balance"] != "0.00":
            raise ConflictError("account balance must be zero to close")
        self.conn.execute("UPDATE accounts SET status=? WHERE id=?", (status, account_id))
        self.conn.commit()
        return self.get(account_id)
