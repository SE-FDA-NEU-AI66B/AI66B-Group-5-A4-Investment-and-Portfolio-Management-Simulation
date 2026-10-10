"""Atomic, newer-only storage for validated provider events."""

import sqlite3
from contextlib import closing
from pathlib import Path


def write_dnse_event(path, event):
    """Apply one validated event with an atomic newer-only comparison."""
    with closing(sqlite3.connect(
        Path(path).resolve().as_uri() + "?mode=rw", uri=True
    )) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute(
            "SELECT 1 FROM price_quote WHERE source NOT IN ('seed', 'dnse') LIMIT 1"
        ).fetchone():
            raise sqlite3.IntegrityError("DNSE worker cannot write a simulation database")
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
    with closing(sqlite3.connect(
        Path(path).resolve().as_uri() + "?mode=ro", uri=True
    )) as connection, connection:
        return {row[0] for row in connection.execute("SELECT symbol FROM instrument")}
