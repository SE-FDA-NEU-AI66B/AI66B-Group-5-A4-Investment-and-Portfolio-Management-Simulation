"""DNSE OHLC candles: signed REST history plus streamed one-minute bars.

History comes from GET /price/ohlc, which returns parallel t/o/h/l/c/v arrays
(the official SDK reads exactly these keys). Streamed bars arrive on the
`ohlc.1.json` channel as T="b" (forming) or T="bc" (closed). Equity prices are
thousands of VND, as in the tick stream; they are converted with Decimal.
"""

import json
import logging
import re
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, DecimalException
from pathlib import Path
from urllib.error import HTTPError, URLError

from virtutrade.dnse import snapshot
from virtutrade.dnse.worker import InvalidEvent

LOGGER = logging.getLogger(__name__)
STORED_RESOLUTIONS = ("1", "1D")
MAX_BARS = 10000
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
# The latest-trade loop runs every 60 seconds; refresh candles every fifth pass.
BAR_REFRESH_PASSES = 5
FIRST_WINDOW = {"1D": 700 * 86400, "1": 5 * 86400}
REPAIR_WINDOW = {"1D": 10 * 86400, "1": 86400}
MINUTE_RETENTION_SECONDS = 30 * 86400


class BarAccessDenied(Exception):
    """DNSE refused OHLC access; candles stop, the quote feed keeps running."""


@dataclass(frozen=True)
class Bar:
    symbol: str
    resolution: str
    bar_time: int
    open_vnd: int
    high_vnd: int
    low_vnd: int
    close_vnd: int
    volume: int


def _price(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise InvalidEvent("Invalid bar price")
    try:
        price = (Decimal(str(value)) * 1000).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    except DecimalException as exc:
        raise InvalidEvent("Invalid bar price") from exc
    if not price.is_finite() or not 0 < price <= 10**12:
        raise InvalidEvent("Invalid bar price")
    return int(price)


def _volume(value):
    if isinstance(value, bool):
        raise InvalidEvent("Invalid bar volume")
    try:
        volume = Decimal(str(value))
    except DecimalException as exc:
        raise InvalidEvent("Invalid bar volume") from exc
    if not volume.is_finite() or volume < 0 or volume != volume.to_integral_value():
        raise InvalidEvent("Invalid bar volume")
    return int(volume)


def make_bar(symbol, resolution, stamp, open_, high, low, close, volume, *, now=None):
    if resolution not in STORED_RESOLUTIONS:
        raise InvalidEvent("Unsupported resolution")
    limit = (time.time() if now is None else now) + 300
    if type(stamp) is not int or not 0 < stamp <= limit:
        raise InvalidEvent("Invalid bar time")
    bar = Bar(symbol, resolution, stamp, _price(open_), _price(high), _price(low),
              _price(close), _volume(volume))
    if not (bar.low_vnd <= min(bar.open_vnd, bar.close_vnd)
            and bar.high_vnd >= max(bar.open_vnd, bar.close_vnd)):
        raise InvalidEvent("Inconsistent bar range")
    return bar


def parse_history(payload, symbol, resolution, *, now=None):
    """Return valid bars, skipping single malformed bars; reject a bad envelope."""
    if not isinstance(payload, dict):
        raise InvalidEvent("Invalid OHLC response")
    columns = [payload.get(key) for key in ("t", "o", "h", "l", "c", "v")]
    if all(column is None for column in columns):
        return []
    if not all(isinstance(column, list) for column in columns):
        raise InvalidEvent("Invalid OHLC response")
    size = len(columns[0])
    if size > MAX_BARS or any(len(column) != size for column in columns):
        raise InvalidEvent("Invalid OHLC response")
    bars = []
    for row in zip(*columns):
        try:
            bars.append(make_bar(symbol, resolution, *row, now=now))
        except InvalidEvent:
            continue
    return bars


def parse_stream_bar(message, symbols, *, now=None):
    if message.get("T") not in ("b", "bc") or message.get("symbol") not in symbols:
        raise InvalidEvent("Unsupported bar event")
    if str(message.get("resolution")) != "1":
        raise InvalidEvent("Unsupported resolution")
    return make_bar(message["symbol"], "1", message.get("time"), message.get("open"),
                    message.get("high"), message.get("low"), message.get("close"),
                    message.get("volume"), now=now)


def write_bars(path, bars):
    """Upsert bars; a forming bar only replaces one with no more volume than it."""
    if not bars:
        return 0
    with closing(sqlite3.connect(
        Path(path).resolve().as_uri() + "?mode=rw", uri=True
    )) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute(
            "SELECT 1 FROM price_quote WHERE source NOT IN ('seed', 'dnse') LIMIT 1"
        ).fetchone():
            raise sqlite3.IntegrityError("DNSE worker cannot write a simulation database")
        changed = 0
        for bar in bars:
            changed += connection.execute(
                "INSERT INTO price_bar(instrument_id, resolution, bar_time, open_vnd, "
                "high_vnd, low_vnd, close_vnd, volume) SELECT id, ?, ?, ?, ?, ?, ?, ? "
                "FROM instrument WHERE symbol = ? "
                "ON CONFLICT(instrument_id, resolution, bar_time) DO UPDATE SET "
                "open_vnd = excluded.open_vnd, high_vnd = excluded.high_vnd, "
                "low_vnd = excluded.low_vnd, close_vnd = excluded.close_vnd, "
                "volume = excluded.volume WHERE excluded.volume >= price_bar.volume",
                (bar.resolution, bar.bar_time, bar.open_vnd, bar.high_vnd, bar.low_vnd,
                 bar.close_vnd, bar.volume, bar.symbol),
            ).rowcount
        return changed


def prune_minute_bars(path, *, now=None):
    cutoff = int(time.time() if now is None else now) - MINUTE_RETENTION_SECONDS
    with closing(sqlite3.connect(
        Path(path).resolve().as_uri() + "?mode=rw", uri=True
    )) as connection, connection:
        return connection.execute(
            "DELETE FROM price_bar WHERE resolution = '1' AND bar_time < ?", (cutoff,)
        ).rowcount


def fetch_history(settings, symbol, resolution, start, end):
    if symbol not in settings.symbols or not re.fullmatch(r"[A-Z][A-Z0-9]{2,9}", symbol):
        raise ValueError("Unsupported OHLC symbol")
    if resolution not in STORED_RESOLUTIONS:
        raise ValueError("Unsupported OHLC resolution")
    request = snapshot.signed_request(settings, "/price/ohlc", {
        "type": "STOCK", "symbol": symbol, "resolution": resolution,
        "from": int(start), "to": int(end),
    })
    try:
        with snapshot.build_opener(snapshot.NoRedirect()).open(request, timeout=15) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise snapshot.SnapshotUnavailable("DNSE OHLC response is too large.")
        return json.loads(raw, parse_float=Decimal)
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise BarAccessDenied("DNSE refused OHLC access.") from None
        raise snapshot.SnapshotUnavailable("DNSE OHLC request is unavailable.") from None
    except (URLError, OSError, ValueError):
        raise snapshot.SnapshotUnavailable("DNSE OHLC request is unavailable.") from None


class BarHistory:
    """Backfill once per symbol, then repair a short recent window each pass."""

    def __init__(self, settings, database, *, fetch=fetch_history, clock=time.time):
        self.settings = settings
        self.database = database
        self.fetch = fetch
        self.clock = clock
        self.loaded = set()
        self.disabled = False

    def refresh(self):
        if self.disabled:
            return 0
        now = int(self.clock())
        written = 0
        for symbol in self.settings.symbols:
            for resolution in STORED_RESOLUTIONS:
                key = (symbol, resolution)
                window = REPAIR_WINDOW if key in self.loaded else FIRST_WINDOW
                try:
                    payload = self.fetch(self.settings, symbol, resolution,
                                         now - window[resolution], now)
                    bars = parse_history(payload, symbol, resolution, now=now)
                except BarAccessDenied:
                    # Quotes may still be permitted; never stop the tick stream for this.
                    LOGGER.warning("DNSE refused OHLC access; candle history is paused.")
                    self.disabled = True
                    return written
                except (snapshot.SnapshotUnavailable, InvalidEvent):
                    LOGGER.warning("DNSE candles unavailable for %s %s; keeping stored bars.",
                                   symbol, resolution)
                    continue
                written += write_bars(self.database, bars)
                self.loaded.add(key)
        prune_minute_bars(self.database, now=now)
        LOGGER.info("DNSE candle refresh: %d bars written.", written)
        return written
