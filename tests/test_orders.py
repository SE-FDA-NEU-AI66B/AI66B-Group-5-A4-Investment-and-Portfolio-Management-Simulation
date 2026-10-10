"""Real SQLite order rules; auth is an explicit test adapter until #77 lands."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from functools import partial

import pytest

from virtutrade.app import create_app
from virtutrade.orders.errors import OrderError
from virtutrade.orders.repository import order_unit_of_work
from virtutrade.orders.service import execute_buy, preview_order
from virtutrade.simulation.repository import init_demo, simulation_unit_of_work
from virtutrade.simulation.service import refresh_quotes

NOW = datetime.now(timezone.utc)


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "orders.db"
    init_demo(path, now=NOW)
    with closing(sqlite3.connect(path)) as c, c:
        c.execute(
            "INSERT INTO account(id,email,password_hash,created_at) VALUES(1,'test@example.test','test-only',?)",
            (NOW.isoformat(),),
        )
        # This is only the reviewed #80 storage contract, not implemented login.
        c.execute(
            "CREATE TABLE auth_session(id INTEGER PRIMARY KEY,account_id INTEGER,token_hash TEXT,created_at TEXT,expires_at TEXT,revoked_at TEXT)"
        )
        c.execute(
            "INSERT INTO auth_session VALUES(1,1,?,?,?,NULL)",
            ("test-only-hash", NOW.isoformat(), (NOW + timedelta(hours=1)).isoformat()),
        )
    return path


def snapshot(path):
    with closing(sqlite3.connect(path)) as c:
        return tuple(
            c.execute("SELECT * FROM " + table).fetchall()
            for table in ("account", "holding", "trade", "price_quote")
        )


def preview(path, quantity=1000):
    return preview_order(
        1, "buy", "hpg", quantity, partial(order_unit_of_work, path), now=NOW
    )


def buy(path, quantity=1000, stamp=None):
    return execute_buy(
        1,
        "HPG",
        quantity,
        stamp or preview(path, quantity)["quote"]["quoted_at"],
        partial(order_unit_of_work, path),
        now=NOW,
    )


def test_preview_no_writes_and_buy_persists(database):
    before = snapshot(database)
    p = preview(database)
    assert p["estimate_vnd"] == 28_000_000 and p["can_submit"]
    assert snapshot(database) == before
    r = buy(database)
    assert r["cash_vnd"] == 72_000_000
    assert r["holding"] == {
        "symbol": "HPG",
        "quantity": 1000,
        "cost_basis_vnd": 28_000_000,
    }
    assert len(snapshot(database)[2]) == 1


def test_warning_disables_and_correction_reenables(database):
    with closing(sqlite3.connect(database)) as c, c:
        c.execute("UPDATE account SET cash_vnd=500000")
    assert preview(database, 30)["shortfall_vnd"] == 340_000
    assert not preview(database, 30)["can_submit"]
    assert preview(database, 10)["can_submit"]
    before = snapshot(database)
    with pytest.raises(OrderError, match="Insufficient cash"):
        buy(database, 30)
    assert snapshot(database) == before


@pytest.mark.parametrize(
    "quantity", [0, -1, True, 1.5, "1", None, 9_007_199_254_740_992]
)
def test_invalid_quantity_never_writes(database, quantity):
    before = snapshot(database)
    with pytest.raises(OrderError) as error:
        buy(database, quantity, stamp="present")
    assert error.value.code == "INVALID_QUANTITY"
    assert snapshot(database) == before


def test_concurrent_buys_recheck_balance(database):
    stamp = preview(database, 2000)["quote"]["quoted_at"]

    def attempt(_):
        try:
            return buy(database, 2000, stamp)["cash_vnd"]
        except OrderError as e:
            return e.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, range(2)))
    assert sorted(map(str, outcomes)) == ["44000000", "INSUFFICIENT_CASH"]
    state = snapshot(database)
    assert len(state[2]) == 1 and state[1][0][3] == 2000


def test_failed_trade_insert_rolls_back_cash_and_holding(database):
    with closing(sqlite3.connect(database)) as c:
        c.execute(
            "CREATE TRIGGER fail_fill BEFORE INSERT ON trade BEGIN SELECT RAISE(ABORT, 'test'); END"
        )
    before = snapshot(database)
    with pytest.raises(OrderError) as e:
        buy(database)
    assert e.value.code == "SERVICE_UNAVAILABLE"
    assert snapshot(database) == before


@pytest.mark.parametrize(
    "change,code",
    [
        ("UPDATE auth_session SET revoked_at='2026-01-01T00:00:00Z'", "AUTH_REQUIRED"),
        ("UPDATE auth_session SET expires_at='2000-01-01T00:00:00Z'", "AUTH_REQUIRED"),
        ("UPDATE account SET status='disabled'", "ACCOUNT_DISABLED"),
        ("UPDATE price_quote SET quoted_at='2000-01-01T00:00:00Z'", "QUOTE_STALE"),
        ("UPDATE price_quote SET quoted_at='2099-01-01T00:00:00Z'", "QUOTE_STALE"),
    ],
)
def test_execution_revalidates_session_account_and_quote(database, change, code):
    stamp = preview(database)["quote"]["quoted_at"]
    with closing(sqlite3.connect(database)) as c, c:
        c.execute(change)
    before = snapshot(database)
    with pytest.raises(OrderError) as e:
        buy(database, stamp=stamp)
    assert e.value.code == code and snapshot(database) == before


def test_simulation_refresh_invalidates_preview_without_resetting_portfolio(database):
    buy(database, 1)
    previous = preview(database)["quote"]["quoted_at"]
    before = snapshot(database)
    result = refresh_quotes(
        1, partial(simulation_unit_of_work, database), now=NOW + timedelta(seconds=1)
    )
    assert result["source"] == "simulation" and result["updated"] == 12
    assert snapshot(database)[:3] == before[:3]
    with pytest.raises(OrderError) as e:
        buy(database, stamp=previous)
    assert e.value.code == "QUOTE_CHANGED"


def test_demo_init_never_resets_existing_file(database):
    before = database.read_bytes()
    with pytest.raises(FileExistsError):
        init_demo(database)
    assert database.read_bytes() == before


def test_demo_refresh_rejects_seed_or_nonadvancing_time(database):
    before = snapshot(database)
    with pytest.raises(OrderError) as e:
        refresh_quotes(1, partial(simulation_unit_of_work, database), now=NOW)
    assert (
        e.value.code == "SIMULATION_CLOCK_NOT_ADVANCED" and snapshot(database) == before
    )
    with closing(sqlite3.connect(database)) as c, c:
        c.execute("UPDATE price_quote SET source='dnse' WHERE id=1")
    before = snapshot(database)
    with pytest.raises(OrderError) as e:
        refresh_quotes(
            1,
            partial(simulation_unit_of_work, database),
            now=NOW + timedelta(seconds=1),
        )
    assert e.value.code == "SIMULATION_DISABLED" and snapshot(database) == before


def test_routes_fail_closed_then_use_explicit_test_auth_adapter(database):
    app = create_app(
        {"TESTING": True, "DATABASE": str(database), "QUOTE_MODE": "simulation"}
    )
    client = app.test_client()
    before = snapshot(database)
    assert client.post("/api/orders/buy", json={}).status_code == 503
    assert b'href="/trade"' in client.get("/market").data
    assert b"Confirm buy" in client.get("/trade").data
    assert b"Simulation / generated" in client.get("/market").data
    assert snapshot(database) == before

    def identity(request):
        if request.headers.get("X-CSRF-Token") != "test-csrf":
            raise OrderError("CSRF_FAILED", "Reload the form and try again.")
        return 1

    app.extensions["orders_identity"] = identity
    headers = {"X-CSRF-Token": "test-csrf"}
    assert client.post("/api/orders/preview", json={}).status_code == 403
    p = client.post(
        "/api/orders/preview",
        json={"side": "buy", "symbol": "HPG", "quantity": 1000},
        headers=headers,
    )
    assert p.status_code == 200 and p.headers["Cache-Control"] == "no-store"
    payload = {
        "symbol": "HPG",
        "quantity": 1000,
        "expected_quote_at": p.json["quote"]["quoted_at"],
    }
    assert (
        client.post(
            "/api/orders/buy", json=dict(payload, account_id=2), headers=headers
        ).status_code
        == 422
    )
    result = client.post("/api/orders/buy", json=payload, headers=headers)
    assert result.status_code == 201 and result.json["cash_vnd"] == 72_000_000
