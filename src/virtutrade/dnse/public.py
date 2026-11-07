"""Real DNSE candles without credentials, from DNSE's public chart endpoint.

This is the unauthenticated endpoint behind DNSE's own web price board. It is
not part of the documented OpenAPI: DNSE may change, limit or block it at any
time, so it is opt-in (MARKET_FEED=dnse-public or `python -m virtutrade
public-feed`) and polled gently. Prefer the signed `stream` worker whenever a
valid API key is available.

It returns the same parallel t/o/h/l/c/v arrays (equity prices in thousands of
VND) as the signed /price/ohlc route, so candles reuse dnse.bars parsing and
storage. The latest one-minute candle becomes the stored quote, timestamped at
its opening minute so it never looks fresher than it is. The previous session's
daily close becomes the reference price for the current session.
"""

import json
import logging
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request

from virtutrade.dnse import snapshot
from virtutrade.dnse.bars import (
    MAX_RESPONSE_BYTES,
    InvalidEvent,
    parse_history,
    prune_minute_bars,
    write_bars,
)
from virtutrade.dnse.repository import read_symbols, write_dnse_event
from virtutrade.dnse.worker import MAX_SYMBOLS, Event
from virtutrade.market.service import VIETNAM

LOGGER = logging.getLogger(__name__)
URL = "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
USER_AGENT = "VirtuTrade/0.1 (student paper-trading project; read-only, polls once a minute)"
POLL_SECONDS = 60
# Daily candles change once a session; refresh them every 15th pass.
DAILY_PASSES = 15
FIRST_WINDOW = {"1": 5 * 86400, "1D": 700 * 86400}
REPAIR_WINDOW = {"1": 86400, "1D": 10 * 86400}


def history_request(symbol, resolution, start, end):
    if not re.fullmatch(r"[A-Z][A-Z0-9]{2,9}", symbol) or resolution not in FIRST_WINDOW:
        raise ValueError("Unsupported public chart request")
    query = urlencode({"symbol": symbol, "resolution": resolution,
                       "from": int(start), "to": int(end)})
    # No credentials: this endpoint is public, so nothing secret can leak.
    return Request(f"{URL}?{query}", headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/json"}, method="GET")


def fetch_public(symbol, resolution, start, end):
    request = history_request(symbol, resolution, start, end)
    try:
        with snapshot.build_opener(snapshot.NoRedirect()).open(request, timeout=15) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise snapshot.SnapshotUnavailable("Public chart response is too large.")
        return json.loads(raw, parse_float=Decimal)
    except (HTTPError, URLError, OSError, ValueError):
        raise snapshot.SnapshotUnavailable("Public chart request is unavailable.") from None


def iso(stamp):
    return datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000000000Z")


def session_reference(daily, session_day):
    """Close of the last daily candle before the session's Vietnam date."""
    earlier = [bar for bar in daily
               if datetime.fromtimestamp(bar.bar_time, VIETNAM).date() < session_day]
    return earlier[-1].close_vnd if earlier else None


class PublicMarket:
    """Backfill once, then poll recent candles and derive quotes and references."""

    def __init__(self, database, symbols, *, fetch=fetch_public, clock=time.time):
        self.database = database
        self.symbols = tuple(symbols)
        self.fetch = fetch
        self.clock = clock
        self.loaded = set()
        self.passes = 0

    def candles(self, symbol, resolution, now):
        window = REPAIR_WINDOW if (symbol, resolution) in self.loaded else FIRST_WINDOW
        bars = parse_history(self.fetch(symbol, resolution, now - window[resolution], now),
                             symbol, resolution, now=now)
        write_bars(self.database, bars)
        self.loaded.add((symbol, resolution))
        return bars

    def refresh(self):
        now = int(self.clock())
        daily_pass = self.passes % DAILY_PASSES == 0
        self.passes += 1
        quotes = 0
        for symbol in self.symbols:
            try:
                minutes = self.candles(symbol, "1", now)
                daily = self.candles(symbol, "1D", now) if (
                    daily_pass or (symbol, "1D") not in self.loaded) else []
            except (snapshot.SnapshotUnavailable, InvalidEvent):
                LOGGER.warning("Public DNSE candles unavailable for %s; keeping stored data.", symbol)
                continue
            if not minutes:
                continue
            last = minutes[-1]
            quotes += write_dnse_event(self.database, Event("t", symbol, last.close_vnd,
                                                            iso(last.bar_time)))
            session_day = datetime.fromtimestamp(last.bar_time, VIETNAM).date()
            reference = session_reference(daily, session_day) if daily else None
            if reference:
                midnight = datetime(session_day.year, session_day.month, session_day.day,
                                    tzinfo=VIETNAM)
                write_dnse_event(self.database, Event("sd", symbol, reference,
                                                      iso(int(midnight.timestamp()))))
        prune_minute_bars(self.database, now=now)
        LOGGER.info("Public DNSE refresh: %d newer quotes / %d symbols.", quotes, len(self.symbols))
        return quotes


def run_public_feed(database, *, interval=POLL_SECONDS, stop=None, fetch=fetch_public):
    """Poll until `stop` is set; a busy database or network skips one pass."""
    symbols = sorted(read_symbols(database))[:MAX_SYMBOLS]
    symbols = [symbol for symbol in symbols if re.fullmatch(r"[A-Z][A-Z0-9]{2,9}", symbol)]
    stop = stop or threading.Event()
    market = PublicMarket(database, symbols, fetch=fetch)
    LOGGER.info("Public DNSE chart feed started for %d symbols (unofficial endpoint).",
                len(symbols))
    while not stop.is_set():
        try:
            market.refresh()
        except sqlite3.OperationalError:
            LOGGER.warning("Database busy; skipping one public refresh.")
        stop.wait(interval)
