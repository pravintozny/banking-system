# banking-system

Banking and Loan Management System. This first increment implements the core
modules (stdlib-only Python 3.10+, SQLite persistence, JSON HTTP API).

## Modules
- **Customers** (`bank/customers.py`): registration, contact info, KYC status (PENDING/VERIFIED/REJECTED), identity documents. KYC can only be VERIFIED once a document is on file.
- **Accounts** (`bank/accounts.py`): SAVINGS/CURRENT accounts, generated 12-digit Luhn-checked account numbers, status (ACTIVE/FROZEN/CLOSED), balance, multiple accounts per customer. Accounts require VERIFIED KYC; closing requires zero balance.
- **Transactions** (`bank/transactions.py`): deposits, withdrawals, transfers, unique references (`TXN…`), history, atomic posting with no overdrafts, and reversals (offsetting REVERSAL entry; original marked REVERSED; a reversal cannot be reversed).

Money is stored as integer cents; amounts accept at most 2 decimal places.

## Run
    python -m bank.api --db bank.sqlite3 --port 8000

## API
    POST /customers                      GET/PATCH /customers/{id}
    PUT  /customers/{id}/kyc             POST/GET /customers/{id}/documents
    POST/GET /customers/{id}/accounts    GET /accounts/{id}
    PUT  /accounts/{id}/status           POST /accounts/{id}/deposit | withdraw
    GET  /accounts/{id}/transactions     POST /transfers
    GET  /transactions/{reference}       POST /transactions/{reference}/reverse

## Test
    python3 -m unittest discover -v

Loan management is not included in this increment.
