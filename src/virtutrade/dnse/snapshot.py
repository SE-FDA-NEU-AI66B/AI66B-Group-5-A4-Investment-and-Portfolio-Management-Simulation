"""Read-only latest-trade bootstrap using DNSE's signed REST market endpoint."""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from virtutrade.dnse.repository import write_dnse_event
from virtutrade.dnse.worker import FeedError, InvalidEvent, parse_event, run_feed

LOGGER = logging.getLogger(__name__)
VIETNAM = timezone(timedelta(hours=7))
MAX_RESPONSE_BYTES = 65536
REFRESH_SECONDS = 60


class SnapshotUnavailable(Exception):
    """Safe transient failure; never carries a provider body or request headers."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward signed credentials to a redirect destination.
        return None


def latest_request(settings, symbol):
    """Sign exactly one GET market-data route, using the official SDK protocol."""
    if symbol not in settings.symbols or not re.fullmatch(r"[A-Z][A-Z0-9]{2,9}", symbol):
        raise ValueError("Unsupported snapshot symbol")
    path = f"/price/{symbol}/trades/latest"
    date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
    nonce = uuid4().hex
    value = f"(request-target): get {path}\ndate: {date}\nnonce: {nonce}"
    digest = hmac.new(settings.api_secret.encode(), value.encode(), hashlib.sha256).digest()
    signature = quote(base64.b64encode(digest).decode(), safe="")
    return Request(
        f"https://openapi.dnse.com.vn{path}?boardId=G1",
        headers={
            "Date": date,
            "x-api-key": settings.api_key,
            "version": "2026-07-23",
            "X-Signature": (
                f'Signature keyId="{settings.api_key}",algorithm="hmac-sha256",'
                f'headers="(request-target) date",signature="{signature}",nonce="{nonce}"'
            ),
        },
        method="GET",
    )


def fetch_latest(settings, symbol):
    request = latest_request(settings, symbol)
    try:
        with build_opener(NoRedirect()).open(request, timeout=10) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise SnapshotUnavailable("DNSE latest quote response is too large.")
        return json.loads(raw, parse_float=Decimal)
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise FeedError("DNSE rejected market REST access; check credentials and permissions.") from None
        raise SnapshotUnavailable("DNSE latest quote request is unavailable.") from None
    except (URLError, OSError, ValueError):
        raise SnapshotUnavailable("DNSE latest quote request is unavailable.") from None


def parse_latest(payload, symbol, *, now=None):
    """REST time is GMT+7; G1 price is thousands of VND, as in the tick stream."""
    if not isinstance(payload, dict) or not isinstance(payload.get("trades"), list):
        raise InvalidEvent("Invalid latest trade response")
    trades = payload["trades"]
    if not trades:
        return None
    if len(trades) != 1 or not isinstance(trades[0], dict):
        raise InvalidEvent("Expected one latest trade")
    trade = trades[0]
    value = trade.get("time")
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}", value
    ):
        raise InvalidEvent("Invalid latest trade time")
    try:
        stamp = datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=VIETNAM)
    except ValueError:
        raise InvalidEvent("Invalid latest trade time") from None
    return parse_event(
        {**trade, "T": "t", "time": {
            "Seconds": int(stamp.timestamp()), "Nanos": stamp.microsecond * 1000,
        }},
        (symbol,),
        now=now,
    )


def refresh_latest(settings, database, *, fetch=fetch_latest):
    """Update each ticker independently; transport failure never rewrites cached data."""
    updated = 0
    for symbol in settings.symbols:
        try:
            event = parse_latest(fetch(settings, symbol), symbol)
        except (SnapshotUnavailable, InvalidEvent):
            LOGGER.warning("Latest DNSE quote unavailable for %s; keeping stored data.", symbol)
            continue
        if event is not None:
            updated += write_dnse_event(database, event)
    LOGGER.info("DNSE latest-trade refresh: %d updated / %d symbols.", updated, len(settings.symbols))
    return updated


async def refresh_loop(settings, database):
    while True:
        # Network I/O runs off the event loop so ticks and heartbeats continue.
        await asyncio.to_thread(refresh_latest, settings, database)
        await asyncio.sleep(REFRESH_SECONDS)


async def run_market_feed(settings, database):
    """Run REST catch-up and WebSocket together; cancel the sibling on fatal failure."""
    tasks = [
        asyncio.create_task(run_feed(settings, database)),
        asyncio.create_task(refresh_loop(settings, database)),
    ]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
