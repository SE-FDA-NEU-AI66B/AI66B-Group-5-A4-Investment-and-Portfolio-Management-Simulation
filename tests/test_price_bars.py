"""Candle history: DNSE OHLC ingestion, aggregation and the bars API."""

import asyncio
import base64
import hashlib
import hmac
import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from urllib.error import HTTPError
from urllib.parse import parse_qs, unquote, urlparse

import pytest

from virtutrade.app import create_app
from virtutrade.database import init_database
from virtutrade.dnse import bars, snapshot
from virtutrade.dnse.repository import write_dnse_event
from virtutrade.dnse.worker import Event, InvalidEvent, Settings, session
from virtutrade.market.history import (
    aggregate,
    illustrative_candles,
    price_history,
    tick_size,
    with_today,
)
from virtutrade.market.models import Candle, Quote
from virtutrade.market.repository import SQLiteQuoteRepository

SETTINGS = Settings("fixture-key", "fixture-secret", ("FPT", "HPG"))
# Monday 2 November 2026, 09:15 Vietnam time.
NOW = int(datetime(2026, 11, 2, 2, 15, tzinfo=timezone.utc).timestamp())


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "bars.db"
    init_database(path)
    return path


def udf(times, opens, highs, lows, closes, volumes):
    return {"t": times, "o": opens, "h": highs, "l": lows, "c": closes, "v": volumes}


def stored(path, resolution="1"):
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT i.symbol, b.bar_time, b.open_vnd, b.high_vnd, b.low_vnd, b.close_vnd, b.volume "
            "FROM price_bar b JOIN instrument i ON i.id = b.instrument_id "
            "WHERE b.resolution = ? ORDER BY i.symbol, b.bar_time", (resolution,)).fetchall()


def test_history_converts_thousands_of_vnd_with_decimal_and_skips_bad_bars():
    payload = udf([NOW - 120, NOW - 60, NOW], [Decimal("24.35"), 24.4, 24.5],
                  [24.5, 24.4, 24.6], [24.3, 24.5, 24.4], [24.45, 24.4, 24.55], [1200, 300, "500"])
    result = bars.parse_history(payload, "HPG", "1", now=NOW)
    # The middle bar has low above high: skipped, not stored with a broken range.
    assert [(bar.bar_time, bar.open_vnd, bar.high_vnd, bar.low_vnd, bar.close_vnd, bar.volume)
            for bar in result] == [(NOW - 120, 24350, 24500, 24300, 24450, 1200),
                                   (NOW, 24500, 24600, 24400, 24550, 500)]


@pytest.mark.parametrize("payload", [
    [], "x", {"t": [1], "o": [1]}, udf([1, 2], [1], [1], [1], [1], [1]),
    udf(list(range(bars.MAX_BARS + 1)), *[[1] * (bars.MAX_BARS + 1)] * 5),
])
def test_malformed_history_envelope_is_rejected(payload):
    with pytest.raises(InvalidEvent):
        bars.parse_history(payload, "HPG", "1D", now=NOW)


def test_no_data_response_is_empty_and_future_or_zero_bars_are_skipped():
    assert bars.parse_history({"s": "no_data"}, "HPG", "1D", now=NOW) == []
    payload = udf([NOW + 3600, 0, NOW], [1, 1, 0], [1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1, 1])
    assert bars.parse_history(payload, "HPG", "1", now=NOW) == []


def test_stream_bar_requires_supported_symbol_and_one_minute_resolution():
    message = {"T": "b", "symbol": "HPG", "resolution": "1", "time": NOW, "open": 24.3,
               "high": 24.4, "low": 24.2, "close": 24.35, "volume": 1400, "type": "STOCK"}
    bar = bars.parse_stream_bar(message, SETTINGS.symbols, now=NOW)
    assert (bar.symbol, bar.close_vnd, bar.volume) == ("HPG", 24350, 1400)
    for changes in ({"symbol": "VN30F1M"}, {"resolution": "1D"}, {"T": "t"}, {"volume": -1},
                    {"time": "1"}, {"close": True}):
        with pytest.raises(InvalidEvent):
            bars.parse_stream_bar({**message, **changes}, SETTINGS.symbols, now=NOW)


def test_forming_bar_grows_but_an_older_snapshot_cannot_shrink_it(database):
    def bar(close, volume):
        return bars.Bar("HPG", "1", NOW, 24000, 24600, 23900, close, volume)
    assert bars.write_bars(database, [bar(24100, 100)]) == 1
    assert bars.write_bars(database, [bar(24500, 900)]) == 1
    assert bars.write_bars(database, [bar(24200, 400)]) == 0
    assert stored(database) == [("HPG", NOW, 24000, 24600, 23900, 24500, 900)]
    # An unknown symbol writes nothing rather than failing the batch.
    assert bars.write_bars(database, [bars.Bar("ZZZ", "1", NOW, 1, 1, 1, 1, 1)]) == 0


def test_bars_cannot_be_written_into_a_simulation_database(database):
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE price_quote SET source = 'simulation'")
    with pytest.raises(sqlite3.IntegrityError):
        bars.write_bars(database, [bars.Bar("HPG", "1", NOW, 1, 1, 1, 1, 1)])
    assert stored(database) == []


def test_schema_rejects_inconsistent_ranges(database):
    with sqlite3.connect(database) as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO price_bar VALUES (1, '1', 10, 100, 90, 80, 95, 1)")


def test_history_backfills_then_repairs_and_prunes_old_minutes(database):
    calls = []

    def fetch(settings, symbol, resolution, start, end):
        calls.append((symbol, resolution, end - start))
        return udf([NOW - 60], [24.0], [24.1], [23.9], [24.05], [10])

    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO price_bar VALUES (1, '1', ?, 1, 1, 1, 1, 1)",
                           (NOW - bars.MINUTE_RETENTION_SECONDS - 60,))
    history = bars.BarHistory(SETTINGS, database, fetch=fetch, clock=lambda: NOW)
    assert history.refresh() == 4
    history.refresh()
    assert calls[:4] == [("FPT", "1", bars.FIRST_WINDOW["1"]), ("FPT", "1D", bars.FIRST_WINDOW["1D"]),
                         ("HPG", "1", bars.FIRST_WINDOW["1"]), ("HPG", "1D", bars.FIRST_WINDOW["1D"])]
    assert {window for _, _, window in calls[4:]} == set(bars.REPAIR_WINDOW.values())
    assert [row[1] for row in stored(database)] == [NOW - 60, NOW - 60]


def test_access_denied_pauses_candles_without_stopping_quotes(database, caplog):
    calls = []

    def denied(*args):
        calls.append(args)
        raise bars.BarAccessDenied("fixture-secret")

    history = bars.BarHistory(SETTINGS, database, fetch=denied, clock=lambda: NOW)
    assert history.refresh() == 0 and history.refresh() == 0
    assert len(calls) == 1 and history.disabled
    assert "fixture-secret" not in caplog.text


def test_unavailable_symbol_keeps_stored_bars_and_continues(database):
    def flaky(settings, symbol, resolution, start, end):
        if symbol == "FPT":
            raise snapshot.SnapshotUnavailable("down")
        return udf([NOW - 60], [24.0], [24.1], [23.9], [24.05], [10])

    history = bars.BarHistory(SETTINGS, database, fetch=flaky, clock=lambda: NOW)
    assert history.refresh() == 2
    assert {row[0] for row in stored(database)} == {"HPG"}
    assert ("FPT", "1") not in history.loaded


def test_ohlc_request_signs_path_only_and_maps_failures(monkeypatch):
    captured = []

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
        body = json.dumps(udf([NOW], [24.0], [24.1], [23.9], [24.05], [10])).encode()
        def open(self, request, timeout):
            captured.append(request)
            return Response(self.body)

    monkeypatch.setattr(snapshot, "build_opener", lambda *_: Opener())
    assert bars.fetch_history(SETTINGS, "HPG", "1D", NOW - 86400, NOW)["c"] == [Decimal("24.05")]
    request = captured[0]
    url = urlparse(request.full_url)
    assert (url.scheme, url.netloc, url.path) == ("https", "openapi.dnse.com.vn", "/price/ohlc")
    assert parse_qs(url.query) == {"type": ["STOCK"], "symbol": ["HPG"], "resolution": ["1D"],
                                   "from": [str(NOW - 86400)], "to": [str(NOW)]}
    headers = dict(request.header_items())
    nonce = headers["X-signature"].split('nonce="')[1].split('"')[0]
    signed = f"(request-target): get /price/ohlc\ndate: {headers['Date']}\nnonce: {nonce}"
    expected = base64.b64encode(hmac.new(b"fixture-secret", signed.encode(), hashlib.sha256).digest()).decode()
    assert unquote(headers["X-signature"].split('signature="')[1].split('"')[0]) == expected
    with pytest.raises(ValueError):
        bars.fetch_history(SETTINGS, "MWG", "1D", 0, NOW)
    with pytest.raises(ValueError):
        bars.fetch_history(SETTINGS, "HPG", "5", 0, NOW)

    Opener.body = b"x" * (bars.MAX_RESPONSE_BYTES + 1)
    with pytest.raises(snapshot.SnapshotUnavailable):
        bars.fetch_history(SETTINGS, "HPG", "1", 0, NOW)
    for code, error in ((401, bars.BarAccessDenied), (403, bars.BarAccessDenied),
                        (429, snapshot.SnapshotUnavailable)):
        def fail(self, request, timeout, code=code):
            raise HTTPError(request.full_url, code, "fixture-secret", {}, None)
        monkeypatch.setattr(Opener, "open", fail)
        with pytest.raises(error) as raised:
            bars.fetch_history(SETTINGS, "HPG", "1", 0, NOW)
        assert "fixture-secret" not in str(raised.value)


def test_minutes_group_into_wider_candles():
    minutes = [Candle(NOW + 60 * index, 100 + index, 110 + index, 90 + index, 101 + index, 10)
               for index in range(6)]
    assert aggregate(minutes, 60) == minutes
    # NOW is 09:15 Vietnam time: minutes 0-4 fill one 5-minute candle, minute 5 starts the next.
    assert aggregate(minutes, 300) == [Candle(NOW, 100, 114, 90, 105, 50),
                                       Candle(NOW + 300, 105, 115, 95, 106, 10)]
    assert aggregate(minutes, 3600) == [Candle(NOW - 900, 100, 115, 90, 106, 60)]


def test_today_is_built_from_minutes_until_the_daily_bar_arrives():
    yesterday = Candle(NOW - 86400 - 8100, 100, 120, 90, 110, 1000)
    minutes = [Candle(NOW - 86400, 101, 102, 100, 101, 5),
               Candle(NOW, 111, 115, 108, 112, 7), Candle(NOW + 60, 112, 118, 105, 116, 3)]
    result = with_today([yesterday], minutes)
    midnight = int(datetime(2026, 11, 2, tzinfo=timezone.utc).timestamp()) - 7 * 3600
    assert result == [yesterday, Candle(midnight, 111, 118, 105, 116, 10)]
    assert with_today([], minutes[1:])[0].volume == 10


def dnse_app(database):
    write_dnse_event(database, Event("t", "HPG", 24550, "2026-11-02T02:15:00.000000000Z"))
    return create_app({"DATABASE": str(database), "TESTING": True, "QUOTE_MODE": "dnse"})


def test_api_serves_stored_dnse_candles_and_never_illustrates_them(database):
    client = dnse_app(database).test_client()
    empty = client.get("/api/market/bars/HPG?resolution=1D").get_json()
    assert (empty["source"], empty["bars"]) == ("dnse", [])
    start = NOW - NOW % 900
    bars.write_bars(database, [bars.Bar("HPG", "1", start + 60 * index, 24000 + index, 24600,
                                        23900, 24100 + index, 10) for index in range(16)])
    response = client.get("/api/market/bars/HPG?resolution=15")
    assert response.status_code == 200 and response.headers["Cache-Control"] == "no-store"
    data = response.get_json()
    assert data["source"] == "dnse" and data["quote"]["price_vnd"] == 24550
    assert [(bar["time"], bar["open"], bar["close"], bar["volume"]) for bar in data["bars"]] == [
        (start, 24000, 24114, 150), (start + 900, 24015, 24115, 10)]
    # Demo rows are hidden in DNSE mode, so a demo-only ticker is not found.
    assert client.get("/api/market/bars/FPT").status_code == 404


def test_api_errors_are_safe_and_structured(database, tmp_path):
    client = create_app({"DATABASE": str(database), "TESTING": True}).test_client()
    bad = client.get("/api/market/bars/HPG?resolution=2")
    assert bad.status_code == 400 and bad.get_json()["error"]["code"] == "INVALID_RESOLUTION"
    assert client.get("/api/market/bars/NOPE").get_json()["error"]["code"] == "TICKER_NOT_FOUND"
    missing = create_app({"DATABASE": str(tmp_path / "missing.db"), "TESTING": True}).test_client()
    unavailable = missing.get("/api/market/bars/HPG")
    assert unavailable.status_code == 503
    assert unavailable.get_json()["error"]["code"] == "HISTORY_UNAVAILABLE"


def test_database_created_before_candles_reads_as_empty_history(database):
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE price_bar")
    assert SQLiteQuoteRepository(str(database)).fetch_bars("HPG", "1", 0) == []


def test_demo_quotes_get_labelled_repeatable_history_ending_at_the_stored_price(database):
    client = create_app({"DATABASE": str(database), "TESTING": True}).test_client()
    for resolution in ("1", "5", "15", "1H", "1D"):
        data = client.get(f"/api/market/bars/HPG?resolution={resolution}").get_json()
        assert data["source"] == "illustrative"
        candles = data["bars"]
        assert candles == client.get(f"/api/market/bars/HPG?resolution={resolution}").get_json()["bars"]
        assert candles[-1]["close"] == data["quote"]["price_vnd"]
        assert candles[-1]["open"] == data["quote"]["previous_close_vnd"]
        assert [bar["time"] for bar in candles] == sorted({bar["time"] for bar in candles})
        assert all(0 < bar["low"] <= min(bar["open"], bar["close"]) and
                   bar["high"] >= max(bar["open"], bar["close"]) and bar["volume"] > 0
                   for bar in candles)


def test_illustrative_history_stays_put_when_only_the_simulated_price_moves():
    quote = Quote("HPG", "Hoa Phat", 28000, 27500, "2026-11-02T02:15:00Z", "simulation")
    moved = Quote("HPG", "Hoa Phat", 28400, 27500, "2026-11-02T02:15:00Z", "simulation")
    before, after = illustrative_candles(quote, "1D"), illustrative_candles(moved, "1D")
    assert before[:-1] == after[:-1] and after[-1].close == 28400
    # Session-aware times: no weekend days or lunch-break minutes.
    for candle in illustrative_candles(quote, "15"):
        moment = datetime.fromtimestamp(candle.time + 7 * 3600, timezone.utc)
        minute = moment.hour * 60 + moment.minute
        assert moment.weekday() < 5 and (540 <= minute < 690 or 780 <= minute < 885)


def test_price_history_rejects_unknown_resolution():
    quote = Quote("HPG", "Hoa Phat", 28000, None, "2026-11-02T02:15:00Z", "dnse")
    with pytest.raises(ValueError):
        price_history(None, quote, "2D")
    assert (tick_size(9990), tick_size(10000), tick_size(50000)) == (10, 50, 100)


def test_websocket_session_stores_streamed_one_minute_bars(database):
    messages = [
        json.dumps({"T": "b", "symbol": "HPG", "resolution": "1", "time": NOW, "open": 24.0,
                    "high": 24.2, "low": 23.9, "close": 24.1, "volume": 500}),
        json.dumps({"T": "bc", "symbol": "HPG", "resolution": "1", "time": NOW, "open": 24.0,
                    "high": 24.3, "low": 23.9, "close": 24.2, "volume": 800}),
        json.dumps({"T": "b", "symbol": "HPG", "resolution": "5", "time": NOW, "open": 1,
                    "high": 1, "low": 1, "close": 1, "volume": 1}),
    ]

    class Socket:
        def __init__(self):
            self.inbox = ['{"action":"welcome","session_id":"s"}', '{"a":"auth_success"}']
            self.sent = []
        async def recv(self):
            return self.inbox.pop(0)
        async def send(self, value):
            self.sent.append(json.loads(value))
        def __aiter__(self):
            return self.stream()
        async def stream(self):
            for message in messages:
                yield message

    socket = Socket()
    asyncio.run(session(socket, Settings("k", "s", ("HPG",)), database))
    assert {"name": "ohlc.1.json", "symbols": ["HPG"]} in socket.sent[-1]["channels"]
    assert stored(database) == [("HPG", NOW, 24000, 24300, 23900, 24200, 800)]
