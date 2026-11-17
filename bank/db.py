import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    address TEXT NOT NULL DEFAULT '',
    kyc_status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (kyc_status IN ('PENDING','VERIFIED','REJECTED')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS customer_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    doc_type TEXT NOT NULL,
    doc_number TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (doc_type, doc_number)
);
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    account_type TEXT NOT NULL CHECK (account_type IN ('SAVINGS','CURRENT')),
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','FROZEN','CLOSED')),
    balance_cents INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('DEPOSIT','WITHDRAWAL','TRANSFER','REVERSAL')),
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    from_account_id INTEGER REFERENCES accounts(id),
    to_account_id INTEGER REFERENCES accounts(id),
    status TEXT NOT NULL DEFAULT 'COMPLETED'
        CHECK (status IN ('COMPLETED','REVERSED')),
    reverses_id INTEGER REFERENCES transactions(id),
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tx_from ON transactions(from_account_id);
CREATE INDEX IF NOT EXISTS idx_tx_to ON transactions(to_account_id);
"""


def connect(path=":memory:"):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
