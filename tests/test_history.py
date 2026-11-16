"""US08 transaction history at /history (#162)."""

import sqlite3
from contextlib import closing

import pytest

from virtutrade import create_app
from virtutrade.accounts.service import mint_preauth_csrf
from virtutrade.database import init_database

SECRET = 'test-secret-162'


@pytest.fixture
def app_db(tmp_path):
    database = tmp_path / 'history.db'
    init_database(database)
    return create_app({'TESTING': True, 'DATABASE': str(database), 'SECRET_KEY': SECRET}), database


def sign_up(app, email):
    client = app.test_client()
    response = client.post('/api/accounts', json={'email': email, 'password': 'Password123'},
                           headers={'X-CSRF-Token': mint_preauth_csrf(SECRET)})
    assert response.status_code == 201
    return client


def add_trade(database, email, symbol, side, quantity, price, executed_at, pnl=None):
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO trade(account_id, instrument_id, side, quantity, fill_price_vnd, "
            "realised_pnl_vnd, executed_at) VALUES ((SELECT id FROM account WHERE email = ?), "
            "(SELECT id FROM instrument WHERE symbol = ?), ?, ?, ?, ?, ?)",
            (email, symbol, side, quantity, price, pnl, executed_at))


def rows(page):
    return page.split('<tbody>', 1)[1].split('</tbody>', 1)[0].count('<tr>')


def test_signed_out_visitor_is_sent_to_log_in(app_db):
    app, _ = app_db
    response = app.test_client().get('/history')
    assert response.status_code == 302 and response.headers['Location'].endswith('/login')


def test_empty_history_shows_the_empty_state(app_db):
    app, _ = app_db
    page = sign_up(app, 'new@example.com').get('/history').get_data(as_text=True)
    assert 'No transactions yet' in page and 'Browse the market' in page


def test_trades_are_newest_first_with_value_pnl_and_totals(app_db):
    app, database = app_db
    client = sign_up(app, 'a@example.com')
    add_trade(database, 'a@example.com', 'HPG', 'buy', 10, 28_100, '2026-11-15T13:00:00Z')
    add_trade(database, 'a@example.com', 'HPG', 'sell', 5, 28_250, '2026-11-15T14:00:00Z', 750)
    response = client.get('/history')
    page = response.get_data(as_text=True)
    assert response.headers['Cache-Control'] == 'no-store'
    body = page.split('<tbody>', 1)[1]
    assert body.index('>Sell<') < body.index('>Buy<')
    assert '281,000' in page and '141,250' in page and '+750' in page
    assert '21:00:00 15/11/2026 (UTC+7)' in page
    assert 'no fees or tax' in page
    assert rows(page) == 2


def test_another_accounts_trades_are_never_listed(app_db):
    app, database = app_db
    sign_up(app, 'owner@example.com')
    client = sign_up(app, 'other@example.com')
    add_trade(database, 'owner@example.com', 'FPT', 'buy', 3, 121_200, '2026-11-15T13:00:00Z')
    page = client.get('/history').get_data(as_text=True)
    assert 'No transactions yet' in page
    assert '121,200' not in page and '<option value="FPT"' not in page


def test_filters_by_symbol_side_and_local_date(app_db):
    app, database = app_db
    client = sign_up(app, 'f@example.com')
    add_trade(database, 'f@example.com', 'HPG', 'buy', 10, 28_000, '2026-11-14T16:59:00Z')
    add_trade(database, 'f@example.com', 'HPG', 'buy', 10, 28_000, '2026-11-14T17:00:00Z')
    add_trade(database, 'f@example.com', 'FPT', 'buy', 1, 120_000, '2026-11-15T03:00:00Z')
    add_trade(database, 'f@example.com', 'HPG', 'sell', 5, 29_000, '2026-11-15T04:00:00Z', 5_000)
    assert rows(client.get('/history?symbol=hpg').get_data(as_text=True)) == 3
    assert rows(client.get('/history?side=sell').get_data(as_text=True)) == 1
    # 15/11 in UTC+7 starts at 2026-11-14T17:00:00Z.
    day = client.get('/history?from=2026-11-15&to=2026-11-15').get_data(as_text=True)
    assert rows(day) == 3
    nothing = client.get('/history?symbol=VNM').get_data(as_text=True)
    assert 'No trades match these filters' in nothing


def test_fifty_trades_per_page_with_older_link(app_db):
    app, database = app_db
    client = sign_up(app, 'p@example.com')
    for minute in range(51):
        add_trade(database, 'p@example.com', 'ACB', 'buy', 1, 25_000,
                  f'2026-11-15T10:{minute:02d}:00Z')
    first = client.get('/history').get_data(as_text=True)
    assert rows(first) == 50 and 'Older trades' in first and '51' in first
    second = client.get('/history?page=2').get_data(as_text=True)
    assert rows(second) == 1 and 'Newer trades' in second and 'Older trades' not in second
