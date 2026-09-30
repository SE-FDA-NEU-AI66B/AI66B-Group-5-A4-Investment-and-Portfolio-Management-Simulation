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
    name TEXT NOT NULL,
    reference_price_vnd INTEGER CHECK(reference_price_vnd > 0),
    reference_at TEXT
);
CREATE TABLE IF NOT EXISTS price_quote (
    id INTEGER PRIMARY KEY,
    instrument_id INTEGER NOT NULL UNIQUE REFERENCES instrument(id),
    price_vnd INTEGER NOT NULL CHECK(price_vnd > 0),
    previous_close_vnd INTEGER CHECK(previous_close_vnd > 0),
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

MARKET_QUERY = """SELECT i.symbol, i.name, q.price_vnd,
       CASE WHEN q.source = 'seed' THEN q.previous_close_vnd
            ELSE i.reference_price_vnd END AS previous_close_vnd,
       i.reference_at, q.quoted_at, q.source
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
        migrate_market_data(connection)
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


def migrate_market_data(connection):
    """Upgrade the M2 seed schema atomically, preserving IDs and existing rows."""
    connection.execute("BEGIN IMMEDIATE")
    columns = {row[1] for row in connection.execute("PRAGMA table_info(instrument)")}
    if "reference_price_vnd" not in columns:
        connection.execute(
            "ALTER TABLE instrument ADD COLUMN reference_price_vnd "
            "INTEGER CHECK(reference_price_vnd > 0)"
        )
    if "reference_at" not in columns:
        connection.execute("ALTER TABLE instrument ADD COLUMN reference_at TEXT")
    quote_columns = list(connection.execute("PRAGMA table_info(price_quote)"))
    if any(row[1] == "previous_close_vnd" and row[3] for row in quote_columns):
        # No other table references price_quote. Keep its PK, FK, UNIQUE and CHECKs.
        statement = SCHEMA.split("CREATE TABLE IF NOT EXISTS price_quote (")[1].split(
            ";"
        )[0]
        connection.execute("CREATE TABLE price_quote_upgrade (" + statement)
        connection.execute("INSERT INTO price_quote_upgrade SELECT * FROM price_quote")
        connection.execute("DROP TABLE price_quote")
        connection.execute("ALTER TABLE price_quote_upgrade RENAME TO price_quote")


def write_dnse_event(path, event):
    """Apply one validated event with an atomic newer-only comparison."""
    with sqlite3.connect(
        Path(path).resolve().as_uri() + "?mode=rw", uri=True
    ) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        if event.kind == "sd":
            result = connection.execute(
                "UPDATE instrument SET reference_price_vnd = ?, reference_at = ? "
                "WHERE symbol = ? AND (reference_at IS NULL OR reference_at < ?)",
                (event.price_vnd, event.quoted_at, event.symbol, event.quoted_at),
            )
        else:
            result = connection.execute(
                "INSERT INTO price_quote(instrument_id, price_vnd, previous_close_vnd, "
                "quoted_at, source) SELECT id, ?, NULL, ?, 'dnse' FROM instrument "
                "WHERE symbol = ? ON CONFLICT(instrument_id) DO UPDATE SET "
                "price_vnd = excluded.price_vnd, previous_close_vnd = NULL, "
                "quoted_at = excluded.quoted_at, source = 'dnse' "
                "WHERE price_quote.source = 'seed' OR price_quote.quoted_at < excluded.quoted_at",
                (event.price_vnd, event.quoted_at, event.symbol),
            )
        return result.rowcount > 0


def read_symbols(path):
    with sqlite3.connect(
        Path(path).resolve().as_uri() + "?mode=ro", uri=True
    ) as connection:
        return {row[0] for row in connection.execute("SELECT symbol FROM instrument")}


def read_market(path):
    """Read the on-disk DB; a missing database must not silently become empty."""
    connection = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(MARKET_QUERY).fetchall()]
    finally:
        connection.close()
