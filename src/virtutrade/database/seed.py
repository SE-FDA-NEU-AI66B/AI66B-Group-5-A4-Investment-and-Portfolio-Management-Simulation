"""Idempotent local demo seed; never connects to a market-data provider."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from virtutrade.config import ROOT
from virtutrade.database.migrations import migrate_market_data
from virtutrade.database.schema import SCHEMA


def init_database(path):
    """Add missing demo rows without deleting or overwriting existing data."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    seed = json.loads((ROOT / "data" / "demo-quotes.json").read_text())
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
        connection.execute("BEGIN IMMEDIATE")
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
