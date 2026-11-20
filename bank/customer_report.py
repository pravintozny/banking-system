"""Customer report component: summarizes a customer and their accounts."""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable, List


@dataclass(frozen=True)
class ReportAccount:
    account_id: str
    account_type: str
    balance: Decimal


@dataclass
class CustomerReport:
    customer_id: str
    name: str
    email: str
    accounts: List[ReportAccount] = field(default_factory=list)

    @property
    def total_balance(self) -> Decimal:
        return sum((a.balance for a in self.accounts), Decimal("0"))

    def render(self) -> str:
        lines = [
            f"Customer Report: {self.customer_id} ({self.name})",
            f"Email: {self.email}",
            f"Accounts: {len(self.accounts)}",
        ]
        for a in self.accounts:
            lines.append(f"  {a.account_id:<12} {a.account_type:<10} {a.balance:>14.2f}")
        lines.append(f"Total balance: {self.total_balance:.2f}")
        return "\n".join(lines)


def build_customer_report(
    customer_id: str,
    name: str,
    email: str,
    accounts: Iterable[ReportAccount],
) -> CustomerReport:
    """Build a report with accounts sorted by account id."""
    if not customer_id:
        raise ValueError("customer_id is required")
    if not name:
        raise ValueError("name is required")
    return CustomerReport(
        customer_id, name, email, sorted(accounts, key=lambda a: a.account_id)
    )
