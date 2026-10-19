"""Atomic simulation-only quote initialization and refresh."""

import json
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from virtutrade.config import ROOT
from virtutrade.database import init_database
from virtutrade.orders.errors import OrderError
from virtutrade.orders.repository import OrderRepository


def fixture():
    return json.loads((ROOT / "data/demo-quotes.json").read_text())


def write_batch(connection, now):
    stamp = now.isoformat(timespec="microseconds").replace("+00:00", "Z")
    updated = 0
    for row in fixture():
        cursor = connection.execute(
            "UPDATE price_quote SET price_vnd=?, previous_close_vnd=?, quoted_at=?, source='simulation' "
            "WHERE instrument_id=(SELECT id FROM instrument WHERE symbol=?)",
            (row["price_vnd"], row["previous_close_vnd"], stamp, row["symbol"]),
        )
        updated += cursor.rowcount
    return {"source": "simulation", "generated_at": stamp, "updated": updated}


def init_demo(path, *, now=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental overwriting or resetting existing accounts.
    handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(handle)
    try:
        init_database(path)
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            write_batch(connection, now or datetime.now(timezone.utc))
    except Exception:
        path.unlink()  # Only the file exclusively created by this invocation.
        raise


class SimulationRepository(OrderRepository):
    def quote_sources_and_times(self):
        return self.connection.execute(
            "SELECT source,quoted_at FROM price_quote"
        ).fetchall()

    def write_batch(self, now):
        return write_batch(self.connection, now)


@contextmanager
def simulation_unit_of_work(path):
    try:
        with (
            closing(
                sqlite3.connect(
                    Path(path).resolve().as_uri() + "?mode=rw", uri=True, timeout=3
                )
            ) as connection,
            connection,
        ):
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            yield SimulationRepository(connection)
    except sqlite3.Error as exc:
        raise OrderError(
            "SERVICE_UNAVAILABLE",
            "Demo data is unavailable. Ask the operator to check the simulation setup.",
        ) from exc
