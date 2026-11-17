from decimal import Decimal, InvalidOperation

from .errors import ValidationError


def to_cents(value):
    """Parse a positive monetary amount (str/int/float) into integer cents."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError("amount must be a number")
    if not d.is_finite():
        raise ValidationError("amount must be a number")
    if d <= 0:
        raise ValidationError("amount must be positive")
    if d != d.quantize(Decimal("0.01")):
        raise ValidationError("amount must have at most 2 decimal places")
    return int(d * 100)


def from_cents(cents):
    return f"{Decimal(cents) / 100:.2f}"
