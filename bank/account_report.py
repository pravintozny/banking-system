"""Account report component: builds a statement summary for an account."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class ReportTransaction:
    date: date
    description: str
    amount: Decimal  # positive = credit, negative = debit


@dataclass
class AccountReport:
    account_id: str
    holder_name: str
    opening_balance: Decimal
    closing_balance: Decimal
    total_credits: Decimal
    total_debits: Decimal
    transactions: List[ReportTransaction] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            f"Account Report: {self.account_id} ({self.holder_name})",
            f"Opening balance: {self.opening_balance:.2f}",
        ]
        for t in self.transactions:
            lines.append(f"{t.date.isoformat()}  {t.description:<30} {t.amount:>12.2f}")
        lines += [
            f"Total credits:   {self.total_credits:.2f}",
            f"Total debits:    {self.total_debits:.2f}",
            f"Closing balance: {self.closing_balance:.2f}",
        ]
        return "\n".join(lines)


def build_account_report(
    account_id: str,
    holder_name: str,
    opening_balance: Decimal,
    transactions: Iterable[ReportTransaction],
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> AccountReport:
    """Build a report. Transactions before `start` roll into the opening balance;
    those after `end` are excluded."""
    if start and end and start > end:
        raise ValueError("start must not be after end")
    opening = Decimal(opening_balance)
    selected: List[ReportTransaction] = []
    for t in sorted(transactions, key=lambda t: t.date):
        if start and t.date < start:
            opening += t.amount
        elif end and t.date > end:
            continue
        else:
            selected.append(t)
    credits = sum((t.amount for t in selected if t.amount > 0), Decimal("0"))
    debits = sum((-t.amount for t in selected if t.amount < 0), Decimal("0"))
    return AccountReport(
        account_id, holder_name, opening, opening + credits - debits,
        credits, debits, selected,
    )
