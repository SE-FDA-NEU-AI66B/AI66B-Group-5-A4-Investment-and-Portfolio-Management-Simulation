"""Shared M2 tables and constraints; no trading service is implemented."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS account (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'investor' CHECK(role IN ('investor', 'admin')),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'disabled')),
    cash_vnd INTEGER NOT NULL DEFAULT 100000000 CHECK(cash_vnd >= 0),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS instrument (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS price_quote (
    id INTEGER PRIMARY KEY,
    instrument_id INTEGER NOT NULL UNIQUE REFERENCES instrument(id),
    price_vnd INTEGER NOT NULL CHECK(price_vnd > 0),
    previous_close_vnd INTEGER NOT NULL CHECK(previous_close_vnd > 0),
    quoted_at TEXT NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('seed', 'dnse'))
);
CREATE TABLE IF NOT EXISTS holding (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES account(id),
    instrument_id INTEGER NOT NULL REFERENCES instrument(id),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    cost_basis_vnd INTEGER NOT NULL CHECK(cost_basis_vnd >= 0),
    UNIQUE(account_id, instrument_id)
);
CREATE TABLE IF NOT EXISTS trade (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES account(id),
    instrument_id INTEGER NOT NULL REFERENCES instrument(id),
    side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    fill_price_vnd INTEGER NOT NULL CHECK(fill_price_vnd > 0),
    realised_pnl_vnd INTEGER,
    executed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_event (
    id INTEGER PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES account(id),
    target_account_id INTEGER NOT NULL REFERENCES account(id),
    previous_status TEXT NOT NULL CHECK(previous_status IN ('active', 'disabled')),
    new_status TEXT NOT NULL CHECK(new_status IN ('active', 'disabled')),
    occurred_at TEXT NOT NULL
);
"""
