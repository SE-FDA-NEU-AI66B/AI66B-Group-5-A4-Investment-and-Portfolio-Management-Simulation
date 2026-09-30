"""M2 schema and repeatable demo seed; no trading service is implemented yet."""

import json
import sqlite3
from pathlib import Path

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

MARKET_QUERY = """SELECT i.symbol, i.name, q.price_vnd, q.previous_close_vnd,
       q.quoted_at, q.source
FROM price_quote AS q
JOIN instrument AS i ON i.id = q.instrument_id
ORDER BY i.symbol"""


def init_database(path):
    """Add missing demo rows without deleting or overwriting existing data."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    seed = json.loads((Path(__file__).parent / "data" / "demo-quotes.json").read_text())
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
        for row in seed:
            connection.execute(
                "INSERT INTO instrument(symbol, name) VALUES (?, ?) "
                "ON CONFLICT(symbol) DO NOTHING",
                (row["symbol"], row["name"]),
            )
            instrument_id = connection.execute(
                "SELECT id FROM instrument WHERE symbol = ?", (row["symbol"],)
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO price_quote(instrument_id, price_vnd, previous_close_vnd, "
                "quoted_at, source) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(instrument_id) DO NOTHING",
                (
                    instrument_id,
                    row["price_vnd"],
                    row["previous_close_vnd"],
                    row["quoted_at"],
                    "seed",
                ),
            )
        count = connection.execute("SELECT COUNT(*) FROM price_quote").fetchone()[0]
    return count


def read_market(path):
    """Read the on-disk DB; a missing database must not silently become empty."""
    connection = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(MARKET_QUERY).fetchall()]
    finally:
        connection.close()
