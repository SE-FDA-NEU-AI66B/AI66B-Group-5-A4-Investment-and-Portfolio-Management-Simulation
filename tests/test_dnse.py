import asyncio
import hashlib
import hmac
import json
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from app import create_app
from database import SCHEMA, init_database, read_market, write_dnse_event
from dnse import FeedError, Settings, auth_message, parse_event, run_feed, session


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "feed.db"
    init_database(path)
    return path


def message(kind="t", seconds=None, nanos=100, **changes):
    value = {
        "T": kind,
        "symbol": "HPG",
        "boardId": "G1",
        "matchPrice": 24.35,
        "basicPrice": 24,
        "time": {
            "Seconds": int(time.time()) if seconds is None else seconds,
            "Nanos": nanos,
        },
    }
    value.update(changes)
    return value


def accept(database, data):
    return write_dnse_event(database, parse_event(data, ("HPG",)))


def quote(database):
    client = create_app({"TESTING": True, "DATABASE": str(database)}).test_client()
    response = client.get("/api/market/quotes")
    assert response.headers["Cache-Control"] == "no-store"
    return next(q for q in response.json["quotes"] if q["symbol"] == "HPG")


def test_provider_prices_persist_and_never_use_seed_reference(database):
    now = int(time.time())
    accept(database, message(seconds=now))
    row = quote(database)
    assert row["price_vnd"] == 24350 and row["source"] == "dnse"
    assert row["change"] is None and not row["stale"]
    accept(database, message("sd", seconds=now))
    assert quote(database)["change"] == "1.46"
    init_database(database)
    assert quote(database)["price_vnd"] == 24350
    assert quote(database)["change"] == "1.46"
    page = (
        create_app({"TESTING": True, "DATABASE": str(database)})
        .test_client()
        .get("/market")
    )
    assert b"24,350" in page.data and b"DNSE market data" in page.data


def test_nanosecond_ordering_duplicate_and_restart(database):
    now = int(time.time())
    assert accept(database, message(seconds=now, nanos=101))
    assert not accept(database, message(seconds=now, nanos=101, matchPrice=25))
    assert not accept(database, message(seconds=now, nanos=100, matchPrice=26))
    assert not accept(
        database, message(seconds=now - 1, nanos=999999999, matchPrice=27)
    )
    assert accept(database, message(seconds=now, nanos=102, matchPrice=24.4))
    assert len(read_market(database)) == 12 and quote(database)["price_vnd"] == 24400


def test_reference_before_tick_and_vietnam_date_boundary(database):
    # 16:59:59 UTC and 17:00:00 UTC are different trading dates in Vietnam.
    boundary = int(datetime(2026, 1, 2, 17, tzinfo=timezone.utc).timestamp())
    accept(database, message("sd", seconds=boundary - 1))
    accept(database, message(seconds=boundary))
    assert quote(database)["change"] is None
    assert quote(database)["stale"]
    accept(database, message("sd", seconds=boundary))
    assert quote(database)["change"] == "1.46"
    assert not accept(database, message("sd", seconds=boundary - 1, basicPrice=99))
    assert quote(database)["change"] == "1.46"


@pytest.mark.parametrize(
    "changes",
    [
        {"symbol": "UNKNOWN"},
        {"symbol": None},
        {"boardId": "G4"},
        {"T": "q"},
        {"matchPrice": 0},
        {"matchPrice": -1},
        {"matchPrice": True},
        {"matchPrice": None},
        {"matchPrice": "NaN"},
        {"matchPrice": "Infinity"},
        {"matchPrice": "1e9999999"},
        {"matchPrice": "0.0001"},
        {"matchPrice": "not a price"},
        {"time": None},
        {"time": {}},
        {"time": {"Seconds": True}},
        {"time": {"Seconds": 1, "Nanos": -1}},
        {"time": {"Seconds": 1, "Nanos": 10**9}},
        {"time": {"Seconds": int(time.time()) + 600}},
    ],
)
def test_invalid_event_cannot_mutate_database(database, changes):
    before = read_market(database)
    with pytest.raises(ValueError):
        accept(database, message(**changes))
    assert read_market(database) == before


def test_upgrade_preserves_legacy_rows_and_constraints(tmp_path):
    path = tmp_path / "legacy.db"
    legacy = SCHEMA.replace(
        ",\n    reference_price_vnd INTEGER CHECK(reference_price_vnd > 0),\n    reference_at TEXT",
        "",
    )
    legacy = legacy.replace(
        "previous_close_vnd INTEGER CHECK", "previous_close_vnd INTEGER NOT NULL CHECK"
    )
    with sqlite3.connect(path) as connection:
        connection.executescript(legacy)
        connection.execute(
            "INSERT INTO instrument VALUES (42, 'HPG', 'Existing company')"
        )
        connection.execute(
            "INSERT INTO price_quote VALUES (7, 42, 123456, 100000, '2026-01-01T00:00:00Z', 'seed')"
        )
    init_database(path)
    init_database(path)
    with sqlite3.connect(path) as connection:
        assert (
            connection.execute(
                "SELECT price_vnd FROM price_quote WHERE id = 7"
            ).fetchone()[0]
            == 123456
        )
        assert (
            connection.execute("SELECT name FROM instrument WHERE id = 42").fetchone()[
                0
            ]
            == "Existing company"
        )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE price_quote SET price_vnd = 0 WHERE id = 7")


def test_missing_database_returns_safe_json_error(tmp_path):
    path = tmp_path / "missing.db"
    response = (
        create_app({"TESTING": True, "DATABASE": str(path)})
        .test_client()
        .get("/api/market/quotes")
    )
    assert (
        response.status_code == 503
        and response.json["error"]["code"] == "MARKET_UNAVAILABLE"
    )
    assert not path.exists()


def test_credentials_and_symbols_validate_without_revealing_secrets(
    database, monkeypatch
):
    monkeypatch.delenv("DNSE_API_KEY", raising=False)
    monkeypatch.delenv("DNSE_API_SECRET", raising=False)
    with pytest.raises(FeedError, match="Set DNSE_API_KEY"):
        Settings.from_environment(database)
    monkeypatch.setenv("DNSE_API_KEY", "test-key")
    monkeypatch.setenv("DNSE_API_SECRET", "test-secret")
    monkeypatch.setenv("DNSE_SYMBOLS", "hpg, HPG, FPT")
    settings = Settings.from_environment(database)
    assert settings.symbols == ("FPT", "HPG")
    assert "test-key" not in repr(settings) and "test-secret" not in repr(settings)
    auth = auth_message(settings)
    signed = f"test-key:{auth['timestamp']}:{auth['nonce']}".encode()
    assert (
        auth["signature"]
        == hmac.new(b"test-secret", signed, hashlib.sha256).hexdigest()
    )
    monkeypatch.setenv("DNSE_SYMBOLS", "VN30F1M")
    with pytest.raises(FeedError):
        Settings.from_environment(database)


def test_real_local_websocket_auth_ping_reconnect_and_browser_api(database):
    async def scenario():
        calls = []
        authenticated = []
        server_errors = []
        now = int(time.time())
        settings = Settings("test-key", "test-secret", ("HPG",))

        async def provider(socket):
            try:
                await socket.send(json.dumps({"session_id": "local-test"}))
                auth = json.loads(await socket.recv())
                signed = (
                    f"{auth['api_key']}:{auth['timestamp']}:{auth['nonce']}".encode()
                )
                assert (
                    auth["signature"]
                    == hmac.new(b"test-secret", signed, hashlib.sha256).hexdigest()
                )
                authenticated.append(auth["nonce"])
                await socket.send('{"a":"auth_success"}')
                subscription = json.loads(await socket.recv())
                assert subscription["channels"] == [
                    {"name": "tick.G1.json", "symbols": ["HPG"]},
                    {"name": "security_definition.G1.json", "symbols": ["HPG"]},
                ]
                await socket.send('{"action":"subscribed"}')
                await socket.send('{"action":"ping"}')
                assert json.loads(await socket.recv()) == {"action": "pong"}
                await socket.send("invalid json")
                await socket.send(json.dumps(message("sd", seconds=now)))
                await socket.send(
                    json.dumps(message(seconds=now, nanos=len(authenticated)))
                )
                await socket.send(json.dumps(message(seconds=now - 1, matchPrice=1)))
                await socket.close()
            except (AssertionError, KeyError, ValueError, OSError) as exc:
                server_errors.append(exc)

        async with serve(provider, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]

            def connector(url, **options):
                assert url.startswith("wss://ws-openapi.dnse.com.vn/")
                return connect(f"ws://127.0.0.1:{port}", proxy=None, **options)

            async def sleep(delay):
                calls.append(delay)
                if len(calls) == 2:
                    raise asyncio.CancelledError

            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(
                    run_feed(settings, database, connector=connector, sleep=sleep), 10
                )
        assert not server_errors
        assert len(set(authenticated)) == 2 and calls == [1, 2]
        assert (
            quote(database)["price_vnd"] == 24350
            and quote(database)["change"] == "1.46"
        )

    asyncio.run(scenario())


def test_auth_error_stops_without_retry_or_secret_echo(database, caplog):
    class Socket:
        def __init__(self):
            self.messages = iter(
                ['{"sid":"test"}', '{"action":"auth_error","message":"private-secret"}']
            )

        async def recv(self):
            return next(self.messages)

        async def send(self, value):
            pass

    with pytest.raises(FeedError) as error:
        asyncio.run(
            session(Socket(), Settings("test-key", "test-secret", ("HPG",)), database)
        )
    assert "private-secret" not in str(error.value) + caplog.text


def test_network_retry_backoff_is_capped_and_does_not_rewrite_prices(database):
    calls = []
    before = read_market(database)

    @asynccontextmanager
    async def unavailable(*args, **kwargs):
        raise OSError("offline")
        yield  # pragma: no cover - makes this a context manager

    async def sleep(delay):
        calls.append(delay)
        if len(calls) == 8:
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            run_feed(
                Settings("test-key", "test-secret", ("HPG",)),
                database,
                connector=unavailable,
                sleep=sleep,
            )
        )
    assert calls == [1, 2, 4, 8, 16, 32, 60, 60]
    assert read_market(database) == before
