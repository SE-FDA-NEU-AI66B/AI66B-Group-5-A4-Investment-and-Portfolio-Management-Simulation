"""DNSE G1 equity feed. Run one worker per database with `python app.py stream`."""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, DecimalException
from uuid import uuid4

from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from database import read_symbols, write_dnse_event

URL = "wss://ws-openapi.dnse.com.vn/v1/stream?encoding=json"
LOGGER = logging.getLogger(__name__)


class FeedError(Exception):
    """A safe, locally authored error; never contains provider payloads or secrets."""


class InvalidEvent(ValueError):
    """Provider input violates the feed contract."""


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    api_secret: str = field(repr=False)
    symbols: tuple[str, ...]

    @classmethod
    def from_environment(cls, database):
        key = os.environ.get("DNSE_API_KEY", "").strip()
        secret = os.environ.get("DNSE_API_SECRET", "").strip()
        if not key or not secret:
            raise FeedError(
                "Set DNSE_API_KEY and DNSE_API_SECRET in your local .env first."
            )
        known = read_symbols(database)
        requested = os.environ.get("DNSE_SYMBOLS", "")
        symbols = (
            tuple(sorted(set(requested.split(","))))
            if requested.strip()
            else tuple(sorted(known))
        )
        symbols = tuple(sorted({symbol.strip().upper() for symbol in symbols}))
        if (
            not symbols
            or len(symbols) > 100
            or any(
                not re.fullmatch(r"[A-Z][A-Z0-9]{2,9}", symbol) or symbol not in known
                for symbol in symbols
            )
        ):
            raise FeedError(
                "DNSE_SYMBOLS must contain 1-100 tickers already in instrument."
            )
        return cls(key, secret, symbols)


def auth_message(settings):
    timestamp = int(time.time())
    nonce = uuid4().hex
    signature = hmac.new(
        settings.api_secret.encode(),
        f"{settings.api_key}:{timestamp}:{nonce}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return {
        "action": "auth",
        "api_key": settings.api_key,
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": signature,
    }


@dataclass(frozen=True)
class Event:
    kind: str
    symbol: str
    price_vnd: int
    quoted_at: str


def parse_event(message, symbols, now=None):
    """Validate JSON stock ticks/reference events; keep nanosecond ordering."""
    kind = message.get("T")
    symbol = message.get("symbol")
    if (
        kind not in ("t", "sd")
        or message.get("boardId") != "G1"
        or symbol not in symbols
    ):
        raise InvalidEvent("Unsupported event, board or symbol")
    raw_price = message.get("matchPrice" if kind == "t" else "basicPrice")
    if isinstance(raw_price, bool) or not isinstance(
        raw_price, (int, float, str, Decimal)
    ):
        raise InvalidEvent("Invalid price")
    try:
        # G1 equity prices are quoted in thousands of VND; never use float arithmetic.
        price = Decimal(str(raw_price)) * 1000
        if (
            not price.is_finite()
            or not 0 < price <= 10**12
            or price != price.to_integral_value()
        ):
            raise InvalidEvent("Invalid price")
    except DecimalException as exc:
        raise InvalidEvent("Invalid price") from exc
    stamp = message.get("time")
    if not isinstance(stamp, dict):
        raise InvalidEvent("Invalid timestamp")
    seconds = stamp.get("Seconds", stamp.get("seconds"))
    nanos = stamp.get("Nanos", stamp.get("nanos", 0))
    if (
        type(seconds) is not int
        or type(nanos) is not int
        or seconds <= 0
        or not 0 <= nanos < 10**9
        or seconds > (time.time() if now is None else now) + 300
    ):
        raise InvalidEvent("Invalid timestamp")
    try:
        timestamp = datetime.fromtimestamp(seconds, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
    except (ValueError, OverflowError, OSError) as exc:
        raise InvalidEvent("Invalid timestamp") from exc
    return Event(kind, symbol, int(price), f"{timestamp}.{nanos:09d}Z")


def decode(raw):
    try:
        message = json.loads(raw, parse_float=Decimal)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise InvalidEvent("Invalid JSON") from exc
    if not isinstance(message, dict):
        raise InvalidEvent("Expected a JSON object")
    return message


async def control_message(socket, message):
    action = message.get("action") or message.get("a")
    if action == "ping":
        await socket.send(json.dumps({"action": "pong"}))
    if action in ("auth_error", "error"):
        # Provider error text may echo credentials. Only report a fixed local message.
        raise FeedError(
            "DNSE rejected authentication/subscription; check credentials and access."
        )
    return action


async def session(socket, settings, database):
    welcome = decode(await asyncio.wait_for(socket.recv(), timeout=15))
    await control_message(socket, welcome)
    if not (welcome.get("session_id") or welcome.get("sid")):
        raise FeedError(
            "Unexpected DNSE welcome message; check the current provider protocol."
        )
    await socket.send(json.dumps(auth_message(settings)))

    async def authenticate():
        while True:
            message = decode(await socket.recv())
            if await control_message(socket, message) == "auth_success":
                return

    await asyncio.wait_for(authenticate(), timeout=15)
    await socket.send(
        json.dumps(
            {
                "action": "subscribe",
                "channels": [
                    {"name": name, "symbols": list(settings.symbols)}
                    for name in ("tick.G1.json", "security_definition.G1.json")
                ],
            }
        )
    )
    LOGGER.info(
        "Authenticated; requested G1 tick/reference streams for %d symbols.",
        len(settings.symbols),
    )
    async for raw in socket:
        try:
            message = decode(raw)
            action = await control_message(socket, message)
            if action == "subscribed":
                LOGGER.info("DNSE acknowledged subscription.")
            if action or message.get("T") not in ("t", "sd"):
                continue
            event = parse_event(message, settings.symbols)
        except ValueError:
            LOGGER.warning("Rejected malformed or unsupported DNSE market event.")
            continue
        # SQLite errors are deliberately fatal: do not silently discard valid quotes.
        await asyncio.to_thread(write_dnse_event, database, event)


async def run_feed(settings, database, *, connector=connect, sleep=asyncio.sleep):
    delay = 1
    while True:
        started = time.monotonic()
        try:
            async with connector(
                URL,
                open_timeout=15,
                ping_interval=30,
                ping_timeout=30,
                close_timeout=5,
                max_size=1024 * 1024,
                max_queue=32,
            ) as socket:
                await session(socket, settings, database)
        except (OSError, TimeoutError, asyncio.TimeoutError, WebSocketException):
            LOGGER.warning(
                "DNSE connection unavailable; keeping the last stored quotes."
            )
        except ValueError as exc:
            raise FeedError(
                "Unexpected DNSE handshake format; check provider protocol."
            ) from exc
        # Also reconnect after a normal close (including the provider session limit).
        if time.monotonic() - started >= 60:
            delay = 1
        LOGGER.info("Reconnecting in %d seconds.", delay)
        await sleep(delay)
        delay = min(delay * 2, 60)
