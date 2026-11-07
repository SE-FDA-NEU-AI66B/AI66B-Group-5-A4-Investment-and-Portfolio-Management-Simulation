"""Credential-free DNSE chart feed: request shape, quotes, references and failures."""

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

import pytest

from virtutrade.app import create_app
from virtutrade.database import init_database
from virtutrade.dnse import public, snapshot
from virtutrade.simulation.repository import init_demo

VIETNAM = timezone(timedelta(hours=7))
# Friday 6 November 2026, 14:45 Vietnam time: the last continuous-session minute.
CLOSE = int(datetime(2026, 11, 6, 14, 45, tzinfo=VIETNAM).timestamp())
NOW = CLOSE + 600
THURSDAY = int(datetime(2026, 11, 5, 9, 0, tzinfo=VIETNAM).timestamp())
FRIDAY = int(datetime(2026, 11, 6, 9, 0, tzinfo=VIETNAM).timestamp())


def udf(rows):
    return {"t": [row[0] for row in rows], "o": [row[1] for row in rows],
            "h": [row[2] for row in rows], "l": [row[3] for row in rows],
            "c": [row[4] for row in rows], "v": [row[5] for row in rows], "nextTime": 0}


def fixture(symbol, resolution, start, end):
    if resolution == "1":
        return udf([(CLOSE - 60, 21.15, 21.2, 21.1, 21.15, 1000), (CLOSE, 21.2, 21.2, 21.2, 21.2, 1500)])
    # Thursday closed at 21.5; Friday's forming daily bar must not be its own reference.
    return udf([(THURSDAY, 21.4, 21.6, 21.3, 21.5, 900000), (FRIDAY, 21.15, 21.4, 21.05, 21.2, 800000)])


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "public.db"
    init_database(path)
    return path


def one(path, sql, params=()):
    with sqlite3.connect(path) as connection:
        return connection.execute(sql, params).fetchone()


def test_request_is_public_read_only_and_identifies_the_project():
    request = public.history_request("HPG", "1D", 100, 200)
    url = urlparse(request.full_url)
    assert (url.scheme, url.netloc, url.path) == ("https", "services.entrade.com.vn",
                                                   "/chart-api/v2/ohlcs/stock")
    assert parse_qs(url.query) == {"symbol": ["HPG"], "resolution": ["1D"], "from": ["100"], "to": ["200"]}
    headers = {name.lower(): value for name, value in request.header_items()}
    assert request.method == "GET" and "VirtuTrade" in headers["user-agent"]
    assert not any(name in headers for name in ("x-api-key", "x-signature", "authorization"))
    for symbol, resolution in (("../x", "1D"), ("HPG", "5")):
        with pytest.raises(ValueError):
            public.history_request(symbol, resolution, 0, 1)


def test_refresh_stores_real_candles_quote_and_previous_session_reference(database):
    market = public.PublicMarket(database, ["HPG"], fetch=fixture, clock=lambda: NOW)
    assert market.refresh() == 1
    assert one(database, "SELECT price_vnd, quoted_at, source FROM price_quote q JOIN instrument i "
                         "ON i.id = q.instrument_id WHERE i.symbol = 'HPG'") == (
        21200, "2026-11-06T07:45:00.000000000Z", "dnse")
    assert one(database, "SELECT reference_price_vnd, reference_at FROM instrument WHERE symbol = 'HPG'") == (
        21500, "2026-11-05T17:00:00.000000000Z")
    assert one(database, "SELECT COUNT(*) FROM price_bar WHERE resolution = '1'") == (2,)
    assert one(database, "SELECT COUNT(*) FROM price_bar WHERE resolution = '1D'") == (2,)

    client = create_app({"DATABASE": str(database), "TESTING": True, "QUOTE_MODE": "dnse"}).test_client()
    quote = client.get("/api/market/quotes/HPG").get_json()["quote"]
    assert (quote["price_vnd"], quote["previous_close_vnd"], quote["change"]) == (21200, 21500, "-1.40")
    chart = client.get("/api/market/bars/HPG?resolution=1D").get_json()
    assert chart["source"] == "dnse" and [bar["close"] for bar in chart["bars"]] == [21500, 21200]


def test_daily_candles_refresh_only_every_fifteenth_pass(database):
    calls = []

    def counting(symbol, resolution, start, end):
        calls.append((resolution, end - start))
        return fixture(symbol, resolution, start, end)

    market = public.PublicMarket(database, ["HPG"], fetch=counting, clock=lambda: NOW)
    for _ in range(public.DAILY_PASSES + 1):
        market.refresh()
    daily = [window for resolution, window in calls if resolution == "1D"]
    assert daily == [public.FIRST_WINDOW["1D"], public.REPAIR_WINDOW["1D"]]
    minutes = [window for resolution, window in calls if resolution == "1"]
    assert minutes[0] == public.FIRST_WINDOW["1"] and set(minutes[1:]) == {public.REPAIR_WINDOW["1"]}


def test_an_older_poll_never_replaces_a_newer_quote(database):
    public.PublicMarket(database, ["HPG"], fetch=fixture, clock=lambda: NOW).refresh()

    def earlier(symbol, resolution, start, end):
        return udf([(CLOSE - 3600, 20.0, 20.0, 20.0, 20.0, 1)]) if resolution == "1" else udf([])

    public.PublicMarket(database, ["HPG"], fetch=earlier, clock=lambda: NOW).refresh()
    assert one(database, "SELECT price_vnd FROM price_quote q JOIN instrument i ON i.id = q.instrument_id "
                         "WHERE i.symbol = 'HPG'") == (21200,)


def test_unavailable_or_malformed_symbols_keep_stored_data_and_continue(database, caplog):
    def flaky(symbol, resolution, start, end):
        if symbol == "FPT":
            raise snapshot.SnapshotUnavailable("down")
        if symbol == "MWG":
            return {"t": [1, 2], "o": [1]}
        return fixture(symbol, resolution, start, end)

    market = public.PublicMarket(database, ["FPT", "HPG", "MWG"], fetch=flaky, clock=lambda: NOW)
    assert market.refresh() == 1
    with sqlite3.connect(database) as connection:
        sources = dict(connection.execute(
            "SELECT i.symbol, q.source FROM price_quote q JOIN instrument i ON i.id = q.instrument_id "
            "WHERE i.symbol IN ('FPT', 'HPG', 'MWG')").fetchall())
    assert sources == {"FPT": "seed", "HPG": "dnse", "MWG": "seed"}
    assert "FPT" in caplog.text and "MWG" in caplog.text


def test_fetch_maps_every_transport_failure_to_a_safe_error(monkeypatch):
    class Response:
        def __init__(self, body):
            self.body = body
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self, size):
            return self.body[:size]

    class Opener:
        body = json.dumps(udf([(CLOSE, 21.2, 21.2, 21.2, 21.2, 1)])).encode()
        def open(self, request, timeout):
            return Response(self.body)

    monkeypatch.setattr(snapshot, "build_opener", lambda *_: Opener())
    assert public.fetch_public("HPG", "1", 0, NOW)["t"] == [CLOSE]
    Opener.body = b"x" * (public.MAX_RESPONSE_BYTES + 1)
    with pytest.raises(snapshot.SnapshotUnavailable):
        public.fetch_public("HPG", "1", 0, NOW)
    for failure in (HTTPError("u", 429, "busy", {}, None), URLError("offline"), TimeoutError()):
        def fail(self, request, timeout, failure=failure):
            raise failure
        monkeypatch.setattr(Opener, "open", fail)
        with pytest.raises(snapshot.SnapshotUnavailable):
            public.fetch_public("HPG", "1D", 0, NOW)


def test_public_feed_refuses_a_simulation_database(tmp_path):
    path = tmp_path / "simulation.db"
    init_demo(path)
    with pytest.raises(sqlite3.IntegrityError):
        public.PublicMarket(path, ["HPG"], fetch=fixture, clock=lambda: NOW).refresh()


def test_run_loop_stops_on_request_and_survives_a_busy_database(database, monkeypatch, caplog):
    stop = threading.Event()
    passes = []

    def refresh(self):
        passes.append(True)
        if len(passes) == 1:
            raise sqlite3.OperationalError("database is locked")
        stop.set()

    monkeypatch.setattr(public.PublicMarket, "refresh", refresh)
    public.run_public_feed(database, interval=0, stop=stop, fetch=fixture)
    assert len(passes) == 2 and "skipping one public refresh" in caplog.text
