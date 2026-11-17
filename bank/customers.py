import re
from datetime import date

from .errors import ConflictError, NotFoundError, ValidationError

KYC_STATUSES = ("PENDING", "VERIFIED", "REJECTED")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9 \-]{6,18}$")


def _row(r):
    return dict(r) if r else None


class CustomerService:
    def __init__(self, conn):
        self.conn = conn

    def register(self, first_name, last_name, date_of_birth, email, phone, address=""):
        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        if not first_name or not last_name:
            raise ValidationError("first_name and last_name are required")
        try:
            dob = date.fromisoformat(date_of_birth)
        except (TypeError, ValueError):
            raise ValidationError("date_of_birth must be YYYY-MM-DD")
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if dob > today or age < 18:
            raise ValidationError("customer must be at least 18 years old")
        email = (email or "").strip().lower()
        if not EMAIL_RE.match(email):
            raise ValidationError("invalid email")
        phone = (phone or "").strip()
        if not PHONE_RE.match(phone):
            raise ValidationError("invalid phone")
        if self.conn.execute("SELECT 1 FROM customers WHERE email=?", (email,)).fetchone():
            raise ConflictError("email already registered")
        cur = self.conn.execute(
            "INSERT INTO customers(first_name,last_name,date_of_birth,email,phone,address)"
            " VALUES (?,?,?,?,?,?)",
            (first_name, last_name, dob.isoformat(), email, phone, address or ""),
        )
        self.conn.commit()
        return self.get(cur.lastrowid)

    def get(self, customer_id):
        r = self.conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
        if not r:
            raise NotFoundError("customer not found")
        return dict(r)

    def update_contact(self, customer_id, email=None, phone=None, address=None):
        c = self.get(customer_id)
        if email is not None:
            email = email.strip().lower()
            if not EMAIL_RE.match(email):
                raise ValidationError("invalid email")
            other = self.conn.execute(
                "SELECT id FROM customers WHERE email=? AND id<>?", (email, customer_id)
            ).fetchone()
            if other:
                raise ConflictError("email already registered")
            c["email"] = email
        if phone is not None:
            if not PHONE_RE.match(phone.strip()):
                raise ValidationError("invalid phone")
            c["phone"] = phone.strip()
        if address is not None:
            c["address"] = address
        self.conn.execute(
            "UPDATE customers SET email=?, phone=?, address=? WHERE id=?",
            (c["email"], c["phone"], c["address"], customer_id),
        )
        self.conn.commit()
        return self.get(customer_id)

    def set_kyc_status(self, customer_id, status):
        if status not in KYC_STATUSES:
            raise ValidationError(f"kyc_status must be one of {KYC_STATUSES}")
        self.get(customer_id)
        if status == "VERIFIED" and not self.list_documents(customer_id):
            raise ValidationError("cannot verify KYC without at least one document")
        self.conn.execute("UPDATE customers SET kyc_status=? WHERE id=?", (status, customer_id))
        self.conn.commit()
        return self.get(customer_id)

    def add_document(self, customer_id, doc_type, doc_number):
        self.get(customer_id)
        doc_type = (doc_type or "").strip().upper()
        doc_number = (doc_number or "").strip()
        if not doc_type or not doc_number:
            raise ValidationError("doc_type and doc_number are required")
        if self.conn.execute(
            "SELECT 1 FROM customer_documents WHERE doc_type=? AND doc_number=?",
            (doc_type, doc_number),
        ).fetchone():
            raise ConflictError("document already registered")
        cur = self.conn.execute(
            "INSERT INTO customer_documents(customer_id,doc_type,doc_number) VALUES (?,?,?)",
            (customer_id, doc_type, doc_number),
        )
        self.conn.commit()
        return _row(self.conn.execute(
            "SELECT * FROM customer_documents WHERE id=?", (cur.lastrowid,)).fetchone())

    def list_documents(self, customer_id):
        self.get(customer_id)
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM customer_documents WHERE customer_id=? ORDER BY id", (customer_id,))]
