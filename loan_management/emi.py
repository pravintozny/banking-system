"""EMI (Equated Monthly Installment) calculation for loans.

EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
where P = principal, r = monthly interest rate, n = tenure in months.
All money values use Decimal and are rounded half-up to 2 places.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import List

CENT = Decimal("0.01")
MAX_TENURE_MONTHS = 1200
MAX_ANNUAL_RATE = Decimal("100")


@dataclass(frozen=True)
class InstallmentRow:
    number: int
    emi: Decimal
    principal: Decimal
    interest: Decimal
    balance: Decimal


@dataclass(frozen=True)
class EMIResult:
    emi: Decimal
    total_payment: Decimal
    total_interest: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _validate(principal, annual_rate_percent, tenure_months):
    try:
        p = Decimal(str(principal))
        rate = Decimal(str(annual_rate_percent))
    except (InvalidOperation, ValueError):
        raise ValueError("principal and annual_rate_percent must be numeric")
    if not p.is_finite() or not rate.is_finite():
        raise ValueError("principal and annual_rate_percent must be finite")
    if p <= 0:
        raise ValueError("principal must be greater than zero")
    if rate < 0 or rate > MAX_ANNUAL_RATE:
        raise ValueError(f"annual_rate_percent must be between 0 and {MAX_ANNUAL_RATE}")
    if isinstance(tenure_months, bool) or not isinstance(tenure_months, int):
        raise ValueError("tenure_months must be an integer")
    if tenure_months <= 0 or tenure_months > MAX_TENURE_MONTHS:
        raise ValueError(f"tenure_months must be between 1 and {MAX_TENURE_MONTHS}")
    return p, rate


def _raw_emi(p: Decimal, rate: Decimal, n: int) -> Decimal:
    if rate == 0:
        return p / n
    r = rate / Decimal(12) / Decimal(100)
    growth = (1 + r) ** n
    return p * r * growth / (growth - 1)


def calculate_emi(principal, annual_rate_percent, tenure_months: int) -> EMIResult:
    """Return the monthly EMI and totals. Raises ValueError on invalid input."""
    p, rate = _validate(principal, annual_rate_percent, tenure_months)
    emi = _money(_raw_emi(p, rate, tenure_months))
    total = _money(emi * tenure_months)
    return EMIResult(emi=emi, total_payment=total, total_interest=_money(total - p))


def amortization_schedule(principal, annual_rate_percent, tenure_months: int) -> List[InstallmentRow]:
    """Month-by-month schedule; the final installment absorbs rounding drift."""
    p, rate = _validate(principal, annual_rate_percent, tenure_months)
    emi = _money(_raw_emi(p, rate, tenure_months))
    r = rate / Decimal(12) / Decimal(100)
    balance = _money(p)
    rows: List[InstallmentRow] = []
    for i in range(1, tenure_months + 1):
        interest = _money(balance * r)
        if i == tenure_months:
            princ = balance
            pay = princ + interest
        else:
            pay = emi
            princ = pay - interest
        balance = _money(balance - princ)
        rows.append(InstallmentRow(i, pay, princ, interest, balance))
    return rows
