"""Sell slice tests for #79.

Two layers: the pure sell calculation from `orders/sell.py` (exact integer
allocation, oversell, invalid input, overflow) and the real-SQLite
`execute_sell` flow (proceeds credited, holding shrunk or removed, realised P&L
recorded, rollback on rejection, concurrency). HTTP wiring is exercised through
the explicit test auth adapter, matching `tests/test_orders.py`.
"""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from functools import partial

import pytest

from virtutrade.app import create_app
from virtutrade.orders.errors import OrderError
from virtutrade.orders.models import Holding
from virtutrade.orders.repository import order_unit_of_work
from virtutrade.orders.sell import allocate_cost, calculate_sell
from virtutrade.orders.service import execute_buy, execute_sell, preview_order
from virtutrade.simulation.repository import init_demo

NOW = datetime.now(timezone.utc)
MAX = 9_007_199_254_740_991

# --- Pure calculation: docs/money-rules.md and api-contract.md section 7.1 --


def test_full_sale_matches_us05_one_thousand_hpg():
    """AC: 1,000 HPG bought at 28,000 sold at 30,000 yields 30,000,000 proceeds
    and 2,000,000 realised profit, and the holding is removed."""
    result = calculate_sell(Holding(quantity=1000, cost_basis_vnd=28_000_000),
                            1000, 30_000)
    assert result.proceeds_vnd == 30_000_000
    assert result.allocated_cost_vnd == 28_000_000
    assert result.remaining_quantity == 0
    assert result.remaining_cost_vnd == 0
    assert result.realised_pnl_vnd == 2_000_000


def test_three_partial_sales_allocate_exactly_the_acquisition_cost():
    """money-rules.md rows 2-4: 10,000 over 3 shares has no exact integer
    average, yet the partial allocations still sum to exactly 10,000."""
    holding, allocated_total = Holding(3, 10_000), 0
    for expected_allocated, expected_cost, expected_quantity in [
        (3_333, 6_667, 2),
        (3_334, 3_333, 1),
        (3_333, 0, 0),
    ]:
        result = calculate_sell(holding, 1, 5_000)
        assert result.allocated_cost_vnd == expected_allocated
        allocated_total += result.allocated_cost_vnd
        holding = Holding(expected_quantity, result.remaining_cost_vnd)
        assert (result.remaining_quantity, result.remaining_cost_vnd) == (
            expected_quantity, expected_cost)
    assert allocated_total == 10_000


def test_allocation_never_loses_a_rounding_vnd():
    """allocated + remaining always equals C, even after a one-VND residual."""
    result = calculate_sell(Holding(3, 10_000), 1, 1)
    assert result.allocated_cost_vnd + result.remaining_cost_vnd == 10_000


def test_zero_remaining_basis_is_valid():
    """money-rules.md row 5: 1 VND over 2 shares leaves a zero-cost share."""
    result = calculate_sell(Holding(2, 1), 1, 1)
    assert result.allocated_cost_vnd == 1
    assert result.remaining_cost_vnd == 0


def test_realised_loss_is_allowed():
    """Negative P&L is within range: selling below cost loses money."""
    result = calculate_sell(Holding(100, 5_000_000), 100, 40_000)
    assert result.realised_pnl_vnd == -1_000_000


def test_allocate_cost_full_sale_returns_the_whole_basis():
    assert allocate_cost(28_000_000, 1000, 1000) == 28_000_000


def test_oversell_is_rejected_with_details():
    """BR2 / US05-AC: holding 500, selling 800 is refused with action. No
    negative remaining quantity is ever produced."""
    with pytest.raises(OrderError) as error:
        calculate_sell(Holding(500, 14_000_000), 800, 30_000, symbol="HPG")
    assert error.value.code == "INSUFFICIENT_SHARES"
    assert error.value.details == {"available_quantity": 500,
                                   "requested_quantity": 800}
    assert "500" in error.value.message and "HPG" in error.value.message


@pytest.mark.parametrize("quantity", [0, -1, True, 1.5, "1", None, MAX + 1])
def test_invalid_quantity_is_rejected(quantity):
    with pytest.raises(OrderError) as error:
        calculate_sell(Holding(1000, 28_000_000), quantity, 30_000)
    assert error.value.code == "INVALID_QUANTITY"


@pytest.mark.parametrize("price", [0, -5, 1.5, "1000", None, True, MAX + 1])
def test_invalid_fill_price_is_rejected(price):
    with pytest.raises(OrderError) as error:
        calculate_sell(Holding(1000, 28_000_000), 1, price)
    assert error.value.code == "VALIDATION_ERROR"


def test_proceeds_overflow_is_rejected():
    """Bounded integer arithmetic: price * quantity beyond the JS safe range is
    refused rather than stored."""
    with pytest.raises(OrderError) as error:
        calculate_sell(Holding(MAX, 1), MAX, 2)
    assert error.value.code == "VALIDATION_ERROR"


# --- Real SQLite execution ---------------------------------------------------


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "sell.db"
    init_demo(path, now=NOW)
    with closing(sqlite3.connect(path)) as c, c:
        c.execute(
            "INSERT INTO account(id,email,password_hash,created_at)"
            " VALUES(1,'test@example.test','test-only',?)",
            (NOW.isoformat(),),
        )
        c.execute(
            "INSERT INTO auth_session(id,account_id,token_hash,created_at,"
            "expires_at,last_seen_at) VALUES(1,1,?,?,?,?)",
            ("test-only-hash", NOW.isoformat(),
             (NOW + timedelta(hours=1)).isoformat(), NOW.isoformat()),
        )
    return path


def snapshot(path):
    with closing(sqlite3.connect(path)) as c:
        return tuple(
            c.execute("SELECT * FROM " + table).fetchall()
            for table in ("account", "holding", "trade", "price_quote")
        )


def set_price(path, price_vnd):
    with closing(sqlite3.connect(path)) as c, c:
        c.execute(
            "UPDATE price_quote SET price_vnd=? WHERE instrument_id="
            "(SELECT id FROM instrument WHERE symbol='HPG')",
            (price_vnd,),
        )


def preview(path, side, quantity=1000):
    return preview_order(
        1, side, "HPG", quantity, partial(order_unit_of_work, path), now=NOW
    )


def buy(path, quantity=1000):
    return execute_buy(
        1, "HPG", quantity, preview(path, "buy", quantity)["quote"]["quoted_at"],
        partial(order_unit_of_work, path), now=NOW,
    )


def sell(path, quantity=1000, stamp=None):
    return execute_sell(
        1, "HPG", quantity,
        stamp or preview(path, "sell", quantity)["quote"]["quoted_at"],
        partial(order_unit_of_work, path), now=NOW,
    )


def holding_rows(path):
    with closing(sqlite3.connect(path)) as c:
        return c.execute("SELECT quantity, cost_basis_vnd FROM holding").fetchall()


def test_full_sale_credits_proceeds_and_removes_holding(database):
    buy(database, 1000)
    set_price(database, 30_000)
    result = sell(database, 1000)

    assert result["trade"]["side"] == "sell"
    assert result["trade"]["realised_pnl_vnd"] == 2_000_000
    assert result["cash_vnd"] == 102_000_000
    assert result["holding"] is None
    assert holding_rows(database) == []


def test_partial_sale_keeps_the_remaining_holding(database):
    buy(database, 1000)
    result = sell(database, 400)

    assert result["cash_vnd"] == 83_200_000
    assert result["holding"] == {
        "symbol": "HPG",
        "quantity": 600,
        "cost_basis_vnd": 16_800_000,
    }
    assert holding_rows(database) == [(600, 16_800_000)]


def test_oversell_is_rejected_and_writes_nothing(database):
    buy(database, 500)
    before = snapshot(database)
    with pytest.raises(OrderError) as error:
        sell(database, 800)
    assert error.value.code == "INSUFFICIENT_SHARES"
    assert snapshot(database) == before


def test_sell_revalidates_a_stale_quote(database):
    buy(database, 1000)
    stamp = preview(database, "sell")["quote"]["quoted_at"]
    with closing(sqlite3.connect(database)) as c, c:
        c.execute("UPDATE price_quote SET quoted_at='2000-01-01T00:00:00Z'")
    before = snapshot(database)
    with pytest.raises(OrderError) as error:
        sell(database, 1000, stamp=stamp)
    assert error.value.code == "QUOTE_STALE"
    assert snapshot(database) == before


def test_concurrent_sells_cannot_oversell(database):
    buy(database, 1)
    stamp = preview(database, "sell", 1)["quote"]["quoted_at"]

    def attempt(_):
        try:
            return sell(database, 1, stamp=stamp)["cash_vnd"]
        except OrderError as e:
            return e.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, range(2)))
    assert sorted(map(str, outcomes)) == ["100000000", "INSUFFICIENT_SHARES"]
    assert holding_rows(database) == []


def test_failed_sell_insert_rolls_back_cash_and_holding(database):
    buy(database, 1000)
    with closing(sqlite3.connect(database)) as c:
        c.execute(
            "CREATE TRIGGER fail_sell BEFORE INSERT ON trade"
            " BEGIN SELECT RAISE(ABORT, 'test'); END"
        )
    before = snapshot(database)
    with pytest.raises(OrderError) as error:
        sell(database, 1000)
    assert error.value.code == "SERVICE_UNAVAILABLE"
    assert snapshot(database) == before


def test_trade_page_renders_sell_controls(database):
    app = create_app(
        {"TESTING": True, "DATABASE": str(database), "QUOTE_MODE": "simulation"}
    )
    client = app.test_client()
    assert b"Confirm buy" in client.get("/trade").data
    page = client.get("/trade?side=sell&symbol=HPG")
    assert b"Confirm sell" in page.data
    assert b'name="order-side" content="sell"' in page.data
    # An unknown side falls back to buy so the page never renders an invalid form.
    fallback = client.get("/trade?side=500")
    assert b"Confirm buy" in fallback.data


def test_sell_route_requires_csrf_and_returns_201(database):
    app = create_app(
        {"TESTING": True, "DATABASE": str(database), "QUOTE_MODE": "simulation"}
    )
    client = app.test_client()
    app.extensions.pop("orders_identity")
    before = snapshot(database)
    assert client.post("/api/orders/sell", json={}).status_code == 503
    assert snapshot(database) == before

    def identity(request):
        if request.headers.get("X-CSRF-Token") != "test-csrf":
            raise OrderError("CSRF_FAILED", "Reload the form and try again.")
        return 1

    app.extensions["orders_identity"] = identity
    headers = {"X-CSRF-Token": "test-csrf"}
    p = client.post(
        "/api/orders/preview",
        json={"side": "buy", "symbol": "HPG", "quantity": 1000},
        headers=headers,
    )
    assert client.post(
        "/api/orders/buy",
        json={"symbol": "HPG", "quantity": 1000,
              "expected_quote_at": p.json["quote"]["quoted_at"]},
        headers=headers,
    ).status_code == 201

    set_price(database, 30_000)
    sp = client.post(
        "/api/orders/preview",
        json={"side": "sell", "symbol": "HPG", "quantity": 1000},
        headers=headers,
    )
    assert sp.status_code == 200 and sp.json["can_submit"] is True
    result = client.post(
        "/api/orders/sell",
        json={"symbol": "HPG", "quantity": 1000,
              "expected_quote_at": sp.json["quote"]["quoted_at"]},
        headers=headers,
    )
    assert result.status_code == 201
    assert result.headers["Cache-Control"] == "no-store"
    assert result.json["trade"]["realised_pnl_vnd"] == 2_000_000
    assert result.json["holding"] is None
