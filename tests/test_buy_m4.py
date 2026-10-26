"""Sprint 4 US04/US10 boundaries against a disposable SQLite database."""

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from functools import partial

import pytest

from virtutrade.orders.errors import OrderError
from virtutrade.orders.repository import order_unit_of_work
from virtutrade.orders.service import execute_buy, preview_order
from virtutrade.simulation.repository import init_demo

NOW = datetime(2026, 10, 27, 4, 0, tzinfo=timezone.utc)
PRICE = 28_000  # HPG in the committed simulation fixture; no live feed is used.


@pytest.fixture
def account_db(tmp_path):
    path = tmp_path / "buy-m4.db"
    init_demo(path, now=NOW)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            "INSERT INTO account(id,email,password_hash,created_at) VALUES(1,?,?,?)",
            ("buy-m4@example.test", "test-only", NOW.isoformat()),
        )
        connection.execute(
            "INSERT INTO auth_session(id,account_id,token_hash,created_at,expires_at,last_seen_at) "
            "VALUES(1,1,?,?,?,?)",
            ("test-only", NOW.isoformat(), (NOW + timedelta(hours=1)).isoformat(), NOW.isoformat()),
        )
    return path


def state(path):
    with closing(sqlite3.connect(path)) as connection:
        return (
            connection.execute("SELECT cash_vnd FROM account WHERE id=1").fetchone()[0],
            connection.execute("SELECT COUNT(*) FROM trade").fetchone()[0],
            connection.execute("SELECT quantity FROM holding WHERE account_id=1").fetchone(),
        )


def preview(path, quantity):
    return preview_order(1, "buy", "HPG", quantity, partial(order_unit_of_work, path), now=NOW)


def confirm(path, quantity, stamp):
    return execute_buy(1, "HPG", quantity, stamp, partial(order_unit_of_work, path), now=NOW)


def set_cash(path, cash):
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("UPDATE account SET cash_vnd=? WHERE id=1", (cash,))


def test_tc_us04_01_preview_has_no_write_then_buy_records_exact_amount(account_db):
    before = state(account_db)
    estimate = preview(account_db, 1)
    assert estimate["estimate_vnd"] == PRICE
    assert estimate["can_submit"] is True
    assert state(account_db) == before

    receipt = confirm(account_db, 1, estimate["quote"]["quoted_at"])
    assert receipt["cash_vnd"] == before[0] - PRICE
    assert state(account_db) == (before[0] - PRICE, 1, (1,))


def test_tc_us04_02_zero_quantity_is_rejected_without_trade(account_db):
    before = state(account_db)
    with pytest.raises(OrderError) as error:
        preview(account_db, 0)
    assert error.value.code == "INVALID_QUANTITY"
    assert state(account_db) == before


@pytest.mark.parametrize("age,allowed", [(900, True), (901, False)])
def test_tc_us04_03_quote_age_boundary(account_db, age, allowed):
    stamp = (NOW - timedelta(seconds=age)).isoformat()
    with closing(sqlite3.connect(account_db)) as connection, connection:
        connection.execute(
            "UPDATE price_quote SET quoted_at=? WHERE instrument_id="
            "(SELECT id FROM instrument WHERE symbol='HPG')",
            (stamp,),
        )
    before = state(account_db)
    if allowed:
        assert preview(account_db, 1)["can_submit"] is True
    else:
        with pytest.raises(OrderError) as error:
            preview(account_db, 1)
        assert error.value.code == "QUOTE_STALE"
    assert state(account_db) == before


@pytest.mark.parametrize("cash,allowed", [(PRICE, True), (PRICE - 1, False)])
def test_tc_us10_01_cash_at_exact_cost_and_one_vnd_short(account_db, cash, allowed):
    set_cash(account_db, cash)
    before = state(account_db)
    estimate = preview(account_db, 1)
    assert estimate["can_submit"] is allowed
    assert estimate["shortfall_vnd"] == int(not allowed)
    if not allowed:
        assert "1 VND" in estimate["warning"]
        with pytest.raises(OrderError) as error:
            confirm(account_db, 1, estimate["quote"]["quoted_at"])
        assert error.value.code == "INSUFFICIENT_CASH"
    assert state(account_db) == before


def test_tc_us10_02_reducing_quantity_clears_warning(account_db):
    set_cash(account_db, PRICE)
    blocked = preview(account_db, 2)
    corrected = preview(account_db, 1)
    assert blocked["can_submit"] is False
    assert blocked["warning"]
    assert corrected["can_submit"] is True
    assert corrected["warning"] is None
    assert state(account_db) == (PRICE, 0, None)


def test_tc_us10_03_cash_shortfall_recheck_does_not_write(account_db):
    estimate = preview(account_db, 1)
    set_cash(account_db, PRICE - 1)
    before = state(account_db)
    with pytest.raises(OrderError) as error:
        confirm(account_db, 1, estimate["quote"]["quoted_at"])
    assert error.value.code == "INSUFFICIENT_CASH"
    assert state(account_db) == before
