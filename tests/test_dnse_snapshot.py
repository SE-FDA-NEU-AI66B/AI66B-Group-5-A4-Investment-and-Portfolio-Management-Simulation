"""Catch-up must show actual last trades without inventing freshness or demo prices."""

import asyncio
import base64
import hashlib
import hmac
import sqlite3
from urllib.error import HTTPError, URLError
from urllib.parse import unquote

import pytest

from virtutrade.app import create_app
from virtutrade.database import init_database
from virtutrade.dnse import snapshot
from virtutrade.dnse.repository import write_dnse_event
from virtutrade.dnse.worker import Event, FeedError, InvalidEvent, Settings
from virtutrade.orders.errors import OrderError
from virtutrade.orders.repository import order_unit_of_work
from virtutrade.orders.service import validate_quote

SETTINGS = Settings("fixture-key", "fixture-secret", ("MWG", "FPT"))


def payload(symbol="MWG", **changes):
    return {"trades": [{
        "boardId": "G1", "symbol": symbol, "matchPrice": 74.9,
        "time": "2026-01-20 14:45:03.431", **changes,
    }]}


def test_signed_request_is_get_only_fixed_origin_and_matches_official_protocol():
    req = snapshot.latest_request(SETTINGS, "MWG")
    assert req.full_url == "https://openapi.dnse.com.vn/price/MWG/trades/latest?boardId=G1"
    assert req.method == "GET" and req.data is None
    headers = dict(req.header_items())
    authorization = headers["X-signature"]
    nonce = authorization.split('nonce="')[1].split('"')[0]
    value = "(request-target): get /price/MWG/trades/latest\ndate: " + headers["Date"] + "\nnonce: " + nonce
    expected = base64.b64encode(hmac.new(b"fixture-secret", value.encode(), hashlib.sha256).digest()).decode()
    assert unquote(authorization.split('signature="')[1].split('"')[0]) == expected
    assert headers["Version"] == "2026-07-23"
    assert snapshot.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.test") is None
    with pytest.raises(ValueError):
        snapshot.latest_request(SETTINGS, "../accounts")


def test_rest_vietnam_time_and_price_are_normalized_without_faking_freshness():
    event = snapshot.parse_latest(payload(), "MWG")
    assert event == Event("t", "MWG", 74900, "2026-01-20T07:45:03.431000000Z")
    assert snapshot.parse_latest({"trades": []}, "MWG") is None


@pytest.mark.parametrize("changes", [
    {"matchPrice": True}, {"matchPrice": "NaN"}, {"matchPrice": -1},
    {"matchPrice": "74.90001"}, {"symbol": "HPG"}, {"boardId": "G4"},
    {"time": "2026-01-20T07:45:03Z"}, {"time": "2026-02-30 14:45:03.431"},
    {"time": "2099-01-20 14:45:03.431"},
])
def test_invalid_or_wrong_symbol_snapshot_is_rejected(changes):
    with pytest.raises(InvalidEvent):
        snapshot.parse_latest(payload(**changes), "MWG")


@pytest.mark.parametrize("value", [None, [], {}, {"trades": "bad"}, {"trades": [None]}, {"trades": [{}, {}]}])
def test_malformed_envelope(value):
    with pytest.raises(InvalidEvent):
        snapshot.parse_latest(value, "MWG")


@pytest.mark.parametrize("code", [401, 403, 429, 500, 302])
def test_http_error_never_leaks_provider_payload_or_credentials(monkeypatch, code):
    class Opener:
        def open(self, request, timeout):
            assert timeout == 10
            raise HTTPError(request.full_url, code, "fixture-secret", {}, None)
    monkeypatch.setattr(snapshot, "build_opener", lambda *_: Opener())
    with pytest.raises(FeedError if code in (401, 403) else snapshot.SnapshotUnavailable) as caught:
        snapshot.fetch_latest(SETTINGS, "MWG")
    assert "fixture" not in str(caught.value)


def test_timeout_and_oversized_response_are_safe(monkeypatch):
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self, size):
            assert size == snapshot.MAX_RESPONSE_BYTES + 1
            return b"x" * size
    class Opener:
        def open(self, *_args, **_kwargs):
            return Response()
    monkeypatch.setattr(snapshot, "build_opener", lambda *_: Opener())
    with pytest.raises(snapshot.SnapshotUnavailable):
        snapshot.fetch_latest(SETTINGS, "MWG")
    def unavailable(*_args, **_kwargs):
        raise URLError("fixture-secret")
    monkeypatch.setattr(Opener, "open", unavailable)
    with pytest.raises(snapshot.SnapshotUnavailable, match="unavailable"):
        snapshot.fetch_latest(SETTINGS, "MWG")


def test_refresh_preserves_newer_ticks_and_does_not_turn_missing_data_into_seed(tmp_path):
    path = tmp_path / "market.db"
    init_database(path)
    newer = Event("t", "MWG", 75000, "2026-01-20T07:45:04.000000001Z")
    write_dnse_event(path, newer)
    def fetch(settings, symbol):
        return payload(symbol) if symbol == "MWG" else {"trades": []}
    assert snapshot.refresh_latest(SETTINGS, path, fetch=fetch) == 0
    client = create_app({"TESTING": True, "DATABASE": str(path), "QUOTE_MODE": "dnse"}).test_client()
    quotes = client.get("/api/market/quotes").json["quotes"]
    assert len(quotes) == 1
    assert quotes[0]["price_vnd"] == 75000
    assert quotes[0]["quoted_at"] == newer.quoted_at
    assert quotes[0]["stale"] and quotes[0]["change"] is None
    assert b"demo prices are excluded" in client.get("/market").data
    with order_unit_of_work(path, provider_only=True) as repo:
        # Even direct order requests cannot fall back to a fresh demo price.
        assert repo.quote("FPT").price_vnd is None
        with pytest.raises(OrderError, match="No valid price"):
            validate_quote(repo.quote("FPT"), None)


def test_refresh_replaces_seed_partial_failure_then_restart(tmp_path):
    path = tmp_path / "market.db"
    init_database(path)
    def fetch(settings, symbol):
        if symbol == "FPT":
            raise snapshot.SnapshotUnavailable("unavailable")
        return payload(symbol)
    assert snapshot.refresh_latest(SETTINGS, path, fetch=fetch) == 1
    assert snapshot.refresh_latest(SETTINGS, path, fetch=fetch) == 0
    init_database(path)
    client = create_app({"TESTING": True, "DATABASE": str(path), "QUOTE_MODE": "dnse"}).test_client()
    assert client.get("/api/market/quotes").json["quotes"][0]["price_vnd"] == 74900
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM instrument").fetchone()[0] == 12


def test_fatal_worker_failure_cancels_sibling(monkeypatch):
    stopped = []
    async def websocket(*_):
        try:
            await asyncio.Future()
        finally:
            stopped.append(True)
    async def rejected(*_):
        await asyncio.sleep(0)
        raise FeedError("Rejected")
    monkeypatch.setattr(snapshot, "run_feed", websocket)
    monkeypatch.setattr(snapshot, "refresh_loop", rejected)
    with pytest.raises(FeedError, match="Rejected"):
        asyncio.run(snapshot.run_market_feed(SETTINGS, "unused"))
    assert stopped == [True]
