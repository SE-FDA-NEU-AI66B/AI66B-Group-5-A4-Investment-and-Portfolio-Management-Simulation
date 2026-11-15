"""A moving practice market for simulation databases only.

Each step moves every simulation quote by a small random walk, kept on the HOSE
price step and inside a +/-7% band around the session reference, and records
the move in one-minute and daily candles. Quotes keep source='simulation', so
every page and API keeps labelling them as generated practice prices. A
database holding seed or DNSE quotes is refused, so provider data is never mixed
with generated prices.
"""

import logging
import math
import random
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from virtutrade.market.history import round_to_step, tick_size
from virtutrade.market.service import VIETNAM, parse_timestamp

LOGGER = logging.getLogger(__name__)
# Order confirmation requires the previewed quote time, so a slower default
# leaves time to preview and confirm between two price moves.
DEFAULT_TICK_SECONDS = 20
STEP_VOLATILITY = 0.002
DAILY_LIMIT = 0.07
MINUTE_RETENTION_SECONDS = 30 * 86400

BAR_UPSERT = (
    "INSERT INTO price_bar(instrument_id, resolution, bar_time, open_vnd, high_vnd, low_vnd, "
    "close_vnd, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
    "ON CONFLICT(instrument_id, resolution, bar_time) DO UPDATE SET "
    "high_vnd = MAX(high_vnd, excluded.high_vnd), low_vnd = MIN(low_vnd, excluded.low_vnd), "
    "close_vnd = excluded.close_vnd, volume = volume + excluded.volume"
)


def next_price(price, reference, rng):
    """One random-walk move on the price step, inside the daily band."""
    step = tick_size(reference)
    floor = round_to_step(reference * (1 - DAILY_LIMIT), step, 1)
    ceiling = round_to_step(reference * (1 + DAILY_LIMIT), step, -1)
    proposed = price * math.exp(rng.gauss(0, STEP_VOLATILITY))
    return min(max(round_to_step(proposed, tick_size(proposed), 0), floor), ceiling)


def step(path, *, now=None, rng=random):
    """Advance every simulation quote once; return the number of quotes moved."""
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat(timespec="microseconds").replace("+00:00", "Z")
    seconds = int(now.timestamp())
    today = now.astimezone(VIETNAM).date()
    day_start = int(datetime(today.year, today.month, today.day, tzinfo=VIETNAM).timestamp())
    with closing(sqlite3.connect(
        Path(path).resolve().as_uri() + "?mode=rw", uri=True, timeout=3
    )) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        rows = connection.execute(
            "SELECT instrument_id, price_vnd, previous_close_vnd, quoted_at, source "
            "FROM price_quote ORDER BY instrument_id"
        ).fetchall()
        if not rows or any(row[4] != "simulation" for row in rows):
            raise sqlite3.IntegrityError("The simulator only writes simulation databases")
        for instrument_id, price, reference, quoted_at, _source in rows:
            try:
                same_day = parse_timestamp(quoted_at).astimezone(VIETNAM).date() == today
            except (ValueError, TypeError, AttributeError):
                same_day = False
            if reference is None or not same_day:
                # A new practice session is referenced to the last price.
                reference = price
            price = next_price(price, reference, rng)
            volume = rng.randrange(1, 60) * 100
            connection.execute(
                "UPDATE price_quote SET price_vnd = ?, previous_close_vnd = ?, quoted_at = ? "
                "WHERE instrument_id = ?", (price, reference, stamp, instrument_id))
            for resolution, bar_time in (("1", seconds - seconds % 60), ("1D", day_start)):
                connection.execute(BAR_UPSERT, (instrument_id, resolution, bar_time,
                                                price, price, price, price, volume))
        connection.execute("DELETE FROM price_bar WHERE resolution = '1' AND bar_time < ?",
                           (seconds - MINUTE_RETENTION_SECONDS,))
        return len(rows)


def run_simulator(path, *, interval=DEFAULT_TICK_SECONDS, stop=None, rng=None):
    """Step until `stop` is set; a busy database skips one step instead of stopping."""
    stop = stop or threading.Event()
    rng = rng or random.Random()
    LOGGER.info("Practice market simulator started; prices move every %d seconds.", interval)
    while not stop.is_set():
        try:
            step(path, rng=rng)
        except sqlite3.OperationalError:
            LOGGER.warning("Simulation database busy; skipping one price step.")
        stop.wait(interval)
