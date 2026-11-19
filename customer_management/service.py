import re
from dataclasses import replace

from .models import Customer, _now

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9 \-]{6,18}$")
_UPDATABLE = ("first_name", "last_name", "email", "phone", "address")


class ValidationError(ValueError):
    pass


class DuplicateEmailError(ValueError):
    pass


class CustomerNotFoundError(KeyError):
    pass


class CustomerService:
    """In-memory customer CRUD with validation and unique (case-insensitive) email."""

    def __init__(self):
        self._customers = {}
        self._emails = {}  # normalized email -> customer id
        self._next_id = 1

    @staticmethod
    def _clean(first_name, last_name, email, phone, address):
        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        if not first_name or not last_name:
            raise ValidationError("first_name and last_name are required")
        email = (email or "").strip().lower()
        if not EMAIL_RE.match(email):
            raise ValidationError("invalid email")
        phone = (phone or "").strip()
        if phone and not PHONE_RE.match(phone):
            raise ValidationError("invalid phone")
        return first_name, last_name, email, phone, (address or "").strip()

    def create(self, first_name, last_name, email, phone="", address=""):
        first_name, last_name, email, phone, address = self._clean(
            first_name, last_name, email, phone, address
        )
        if email in self._emails:
            raise DuplicateEmailError("email already registered")
        customer = Customer(self._next_id, first_name, last_name, email, phone, address)
        self._next_id += 1
        self._customers[customer.id] = customer
        self._emails[email] = customer.id
        return customer

    def get(self, customer_id):
        try:
            return self._customers[customer_id]
        except KeyError:
            raise CustomerNotFoundError(f"customer {customer_id} not found") from None

    def update(self, customer_id, **changes):
        current = self.get(customer_id)
        unknown = set(changes) - set(_UPDATABLE)
        if unknown:
            raise ValidationError(f"cannot update: {', '.join(sorted(unknown))}")
        merged = {f: changes.get(f, getattr(current, f)) for f in _UPDATABLE}
        first, last, email, phone, address = self._clean(**merged)
        owner = self._emails.get(email)
        if owner is not None and owner != customer_id:
            raise DuplicateEmailError("email already registered")
        updated = replace(
            current, first_name=first, last_name=last, email=email,
            phone=phone, address=address, updated_at=_now(),
        )
        del self._emails[current.email]
        self._emails[email] = customer_id
        self._customers[customer_id] = updated
        return updated

    def delete(self, customer_id):
        customer = self.get(customer_id)
        del self._customers[customer_id]
        del self._emails[customer.email]

    def list(self, search=None):
        items = sorted(self._customers.values(), key=lambda c: c.id)
        if search:
            s = search.strip().lower()
            items = [
                c for c in items
                if s in c.first_name.lower() or s in c.last_name.lower() or s in c.email
            ]
        return items
