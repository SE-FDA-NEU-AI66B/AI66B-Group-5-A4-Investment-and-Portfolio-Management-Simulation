"""Sprint 4 US05 sell and cost-basis tests for #120.

The cases run against the real sell service and a disposable SQLite database.
They separate preview from confirmation, check exact integer VND, and prove
that rejected sales leave account, holding, trade and quote rows unchanged.
"""

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from functools import partial

import pytest

from virtutrade.app import create_app
from virtutrade.orders.errors import OrderError
from virtutrade.orders.repository import order_unit_of_work
from virtutrade.orders.service import execute_buy, execute_sell, preview_order
from virtutrade.simulation.repository import init_demo

NOW = datetime(2026, 10, 30, 4, 0, tzinfo=timezone.utc)
SELL_PRICE = 30_000
INITIAL_CASH = 100_000_000


@pytest.fixture
def sell_db(tmp_path):
    path = tmp_path / 'sell-m4.db'
    init_demo(path, now=NOW)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            'INSERT INTO account(id,email,password_hash,created_at)'
            ' VALUES(1,?,?,?)',
            ('sell-m4@example.test', 'test-only', NOW.isoformat()),
        )
        connection.execute(
            'INSERT INTO auth_session(id,account_id,token_hash,created_at,'
            'expires_at,last_seen_at) VALUES(1,1,?,?,?,?)',
            ('test-only-hash', NOW.isoformat(),
             (NOW + timedelta(hours=1)).isoformat(), NOW.isoformat()),
        )
    return path


def preview(path, side, quantity):
    return preview_order(
        1, side, 'HPG', quantity, partial(order_unit_of_work, path), now=NOW
    )


def buy(path, quantity):
    stamp = preview(path, 'buy', quantity)['quote']['quoted_at']
    return execute_buy(
        1, 'HPG', quantity, stamp, partial(order_unit_of_work, path), now=NOW
    )


def sell(path, quantity, stamp):
    return execute_sell(
        1, 'HPG', quantity, stamp, partial(order_unit_of_work, path), now=NOW
    )


def set_price(path, price_vnd):
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            "UPDATE price_quote SET price_vnd=? WHERE instrument_id="
            "(SELECT id FROM instrument WHERE symbol='HPG')",
            (price_vnd,),
        )


def set_quote_time(path, stamp):
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            "UPDATE price_quote SET quoted_at=? WHERE instrument_id="
            "(SELECT id FROM instrument WHERE symbol='HPG')",
            (stamp,),
        )


def snapshot(path):
    with closing(sqlite3.connect(path)) as connection:
        return tuple(
            connection.execute('SELECT * FROM ' + table).fetchall()
            for table in ('account', 'holding', 'trade', 'price_quote')
        )


def test_tc_us05_01_partial_then_full_sale_preserves_cash_and_cost_basis(sell_db):
    buy(sell_db, 1000)
    set_price(sell_db, SELL_PRICE)
    before_preview = snapshot(sell_db)

    partial = preview(sell_db, 'sell', 400)
    assert partial['can_submit'] is True
    assert partial['estimate_vnd'] == 12_000_000
    assert partial['available_quantity'] == 1000
    assert snapshot(sell_db) == before_preview

    first = sell(sell_db, 400, partial['quote']['quoted_at'])
    assert first['cash_vnd'] == 84_000_000
    assert first['holding'] == {
        'symbol': 'HPG',
        'quantity': 600,
        'cost_basis_vnd': 16_800_000,
    }
    assert first['trade']['realised_pnl_vnd'] == 800_000
    assert 11_200_000 + first['holding']['cost_basis_vnd'] == 28_000_000

    final = preview(sell_db, 'sell', 600)
    assert final['estimate_vnd'] == 18_000_000
    second = sell(sell_db, 600, final['quote']['quoted_at'])
    assert second['cash_vnd'] == 102_000_000
    assert second['holding'] is None
    assert second['trade']['realised_pnl_vnd'] == 1_200_000
    assert first['trade']['realised_pnl_vnd'] + second['trade']['realised_pnl_vnd'] == 2_000_000
    assert second['cash_vnd'] == INITIAL_CASH + 2_000_000


def test_tc_us05_02_oversell_is_refused_without_writes(sell_db):
    buy(sell_db, 500)
    set_price(sell_db, SELL_PRICE)
    before = snapshot(sell_db)

    preview_result = preview(sell_db, 'sell', 800)
    assert preview_result['can_submit'] is False
    assert preview_result['available_quantity'] == 500
    assert preview_result['warning']
    assert snapshot(sell_db) == before

    with pytest.raises(OrderError) as error:
        sell(sell_db, 800, preview_result['quote']['quoted_at'])
    assert error.value.code == 'INSUFFICIENT_SHARES'
    assert error.value.details == {
        'available_quantity': 500,
        'requested_quantity': 800,
    }
    assert snapshot(sell_db) == before


@pytest.mark.parametrize('quantity,accepted', [(0, False), (1, True),
                                               (1000, True), (1001, False)])
def test_tc_us05_03_quantity_boundaries(sell_db, quantity, accepted):
    buy(sell_db, 1000)
    set_price(sell_db, SELL_PRICE)
    before = snapshot(sell_db)

    if quantity == 0:
        with pytest.raises(OrderError) as error:
            preview(sell_db, 'sell', 0)
        assert error.value.code == 'INVALID_QUANTITY'
        assert snapshot(sell_db) == before
        return

    preview_result = preview(sell_db, 'sell', quantity)
    assert preview_result['can_submit'] is accepted
    if accepted:
        result = sell(sell_db, quantity, preview_result['quote']['quoted_at'])
        assert result['trade']['quantity'] == quantity
        if quantity == 1000:
            assert result['holding'] is None
        else:
            assert result['holding']['quantity'] == 1000 - quantity
    else:
        assert preview_result['warning']
        with pytest.raises(OrderError) as error:
            sell(sell_db, quantity, preview_result['quote']['quoted_at'])
        assert error.value.code == 'INSUFFICIENT_SHARES'
        assert snapshot(sell_db) == before


def test_tc_us05_04_changed_and_stale_quote_are_refused_before_commit(sell_db):
    buy(sell_db, 1000)
    set_price(sell_db, SELL_PRICE)
    first = preview(sell_db, 'sell', 100)
    old_stamp = first['quote']['quoted_at']

    set_quote_time(sell_db, (NOW - timedelta(seconds=10)).isoformat())
    before = snapshot(sell_db)
    with pytest.raises(OrderError) as changed:
        sell(sell_db, 100, old_stamp)
    assert changed.value.code == 'QUOTE_CHANGED'
    assert snapshot(sell_db) == before

    fresh = preview(sell_db, 'sell', 100)
    fresh_stamp = fresh['quote']['quoted_at']
    set_quote_time(sell_db, (NOW - timedelta(seconds=901)).isoformat())
    before = snapshot(sell_db)
    with pytest.raises(OrderError) as stale:
        sell(sell_db, 100, fresh_stamp)
    assert stale.value.code == 'QUOTE_STALE'
    assert snapshot(sell_db) == before


def test_tc_us05_05_sell_route_rejects_oversell_before_write(sell_db):
    buy(sell_db, 500)
    set_price(sell_db, SELL_PRICE)
    set_quote_time(sell_db, datetime.now(timezone.utc).isoformat())
    app = create_app({
        'TESTING': True,
        'DATABASE': str(sell_db),
        'QUOTE_MODE': 'simulation',
    })

    def identity(request):
        if request.headers.get('X-CSRF-Token') != 'test-csrf':
            raise OrderError('CSRF_FAILED', 'Reload the form and try again.')
        return 1

    app.extensions['orders_identity'] = identity
    client = app.test_client()
    headers = {'X-CSRF-Token': 'test-csrf'}
    before = snapshot(sell_db)

    preview_result = client.post(
        '/api/orders/preview',
        json={'side': 'sell', 'symbol': 'HPG', 'quantity': 800},
        headers=headers,
    )
    assert preview_result.status_code == 200
    assert preview_result.get_json()['can_submit'] is False
    assert preview_result.get_json()['available_quantity'] == 500

    rejected = client.post(
        '/api/orders/sell',
        json={
            'symbol': 'HPG',
            'quantity': 800,
            'expected_quote_at': preview_result.get_json()['quote']['quoted_at'],
        },
        headers=headers,
    )
    assert rejected.status_code == 409
    assert rejected.get_json()['error']['code'] == 'INSUFFICIENT_SHARES'
    assert rejected.headers['Cache-Control'] == 'no-store'
    assert snapshot(sell_db) == before
