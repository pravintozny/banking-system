from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


@dataclass
class Customer:
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    address: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
