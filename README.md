# banking-system
## Loan Management / EMI

`loan_management.calculate_emi(principal, annual_rate_percent, tenure_months)` returns the EMI, total payment and total interest; `amortization_schedule(...)` returns the per-month breakdown. Uses `Decimal`, rounds half-up to 2 places, raises `ValueError` on invalid input.

Run tests: `python3 -m unittest discover -s tests -t .`
