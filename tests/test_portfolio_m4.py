"""Sprint 4 US06 private Portfolio states and valuation, for #122.

Each test name carries the case ID listed in docs/testing.md. Every test uses a
throwaway SQLite database under tmp_path and the Flask test client: no server,
no developer database and no market-data provider is involved. Holdings and
quotes are inserted with explicit integers so every expected number is derived
by hand, not read back from the code under test.

TC-US06-01  empty holdings: total = cash, Browse the market visible   normal/boundary
TC-US06-02  populated holding: exact integer value, P&L and total      normal
TC-US06-03  guest and second account: 401 and no private data          error
TC-US06-04  missing or delayed quote: incomplete/delayed, never zero   error
TC-US06-05  quantity/value/percent boundaries                          boundary
TC-US06-06  quote age 900 s vs 901 s                                   boundary
"""

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from virtutrade import create_app
from virtutrade.accounts.service import mint_preauth_csrf
from virtutrade.database import init_database
from virtutrade.portfolio.models import Position
from virtutrade.portfolio.service import value_position

SECRET = 'test-secret-122'
PASSWORD = 'Password123'
GRANT = 100_000_000


def stamp(seconds_ago=0):
    """A quote timestamp relative to the wall clock the app itself uses."""
    moment = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    return moment.strftime('%Y-%m-%dT%H:%M:%SZ')


@pytest.fixture
def app_db(tmp_path):
    database = tmp_path / 'portfolio-m4.db'
    init_database(database)
    app = create_app({'TESTING': True, 'DATABASE': str(database), 'SECRET_KEY': SECRET})
    return app, database


def sign_up(app, email):
    """Register through the real API; the returned client holds the session."""
    client = app.test_client()
    response = client.post(
        '/api/accounts',
        json={'email': email, 'password': PASSWORD},
        headers={'X-CSRF-Token': mint_preauth_csrf(SECRET)},
    )
    assert response.status_code == 201, response.get_json()
    return client


def run(database, statement, params=()):
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(statement, params)


def account_id(database, email):
    with closing(sqlite3.connect(database)) as connection:
        return connection.execute(
            'SELECT id FROM account WHERE email = ?', (email,)
        ).fetchone()[0]


def add_holding(database, email, symbol, quantity, cost_basis, price, quoted_at=None):
    """Insert a test instrument, its latest quote (price=None: no quote row) and
    one holding for `email`. Everything is an explicit integer."""
    owner = account_id(database, email)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute('INSERT INTO instrument(symbol, name) VALUES (?, ?)',
                           (symbol, f'{symbol} test company'))
        instrument = connection.execute(
            'SELECT id FROM instrument WHERE symbol = ?', (symbol,)
        ).fetchone()[0]
        if price is not None:
            connection.execute(
                'INSERT INTO price_quote(instrument_id, price_vnd, quoted_at, source) '
                "VALUES (?, ?, ?, 'seed')",
                (instrument, price, quoted_at or stamp()),
            )
        connection.execute(
            'INSERT INTO holding(account_id, instrument_id, quantity, cost_basis_vnd) '
            'VALUES (?, ?, ?, ?)',
            (owner, instrument, quantity, cost_basis),
        )


def set_cash(database, email, cash):
    run(database, 'UPDATE account SET cash_vnd = ? WHERE email = ?', (cash, email))


def api(client):
    response = client.get('/api/portfolio')
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def only_position(payload):
    assert len(payload['positions']) == 1
    return payload['positions'][0]


# --- TC-US06-01 -------------------------------------------------------------


def test_tc_us06_01_empty_holdings_total_equals_cash_with_browse_market(app_db):
    app, _database = app_db
    client = sign_up(app, 'empty@example.test')

    payload = api(client)
    assert payload['positions'] == []
    assert payload['cash_vnd'] == GRANT
    assert payload['holdings_value_vnd'] == 0
    assert payload['total_value_vnd'] == payload['cash_vnd']
    assert payload['valuation_complete'] is True
    assert payload['unpriced_count'] == 0 and payload['stale_count'] == 0

    page = client.get('/portfolio')
    assert page.status_code == 200
    assert b'No positions yet' in page.data
    assert b'100,000,000 VND' in page.data
    assert b'Browse the market' in page.data and b'href="/market"' in page.data


# --- TC-US06-02 -------------------------------------------------------------


def test_tc_us06_02_one_holding_current_quote_exact_integer_values(app_db):
    app, database = app_db
    client = sign_up(app, 'owner@example.test')
    # 300 shares, cost 8,400,000 (average 28,000), quoted 30,500 now.
    add_holding(database, 'owner@example.test', 'XQA', 300, 8_400_000, 30_500)
    set_cash(database, 'owner@example.test', 12_345_678)

    payload = api(client)
    position = only_position(payload)
    assert position['symbol'] == 'XQA' and position['quantity'] == 300
    assert position['cost_basis_vnd'] == 8_400_000
    assert position['average_cost_vnd'] == '28000'
    assert position['market_value_vnd'] == 9_150_000          # 300 * 30,500
    assert position['unrealised_pnl_vnd'] == 750_000          # 9,150,000 - 8,400,000
    assert position['unrealised_pnl_percent'] == '8.93'       # 750,000 / 8,400,000
    assert position['priced'] is True and position['stale'] is False
    assert payload['cash_vnd'] == 12_345_678
    assert payload['holdings_value_vnd'] == 9_150_000
    assert payload['total_value_vnd'] == 21_495_678           # cash + holdings
    assert payload['valuation_complete'] is True
    for value in (position['market_value_vnd'], position['unrealised_pnl_vnd'],
                  payload['total_value_vnd']):
        assert type(value) is int

    page = client.get('/portfolio').data
    assert b'9,150,000' in page and b'+750,000' in page and b'+8.93%' in page
    assert b'21,495,678 VND' in page


def test_tc_us06_02_only_the_signed_in_accounts_holding_is_counted(app_db):
    app, database = app_db
    client = sign_up(app, 'owner@example.test')
    sign_up(app, 'neighbour@example.test')
    add_holding(database, 'owner@example.test', 'XQA', 10, 100_000, 11_000)
    add_holding(database, 'neighbour@example.test', 'XQB', 9_999, 99_990_000, 50_000)

    payload = api(client)
    assert [p['symbol'] for p in payload['positions']] == ['XQA']
    assert payload['holdings_value_vnd'] == 110_000
    assert payload['total_value_vnd'] == GRANT + 110_000
    assert b'XQB' not in client.get('/portfolio').data


# --- TC-US06-03 -------------------------------------------------------------


def test_tc_us06_03_guest_gets_401_and_no_private_data(app_db):
    app, database = app_db
    sign_up(app, 'owner@example.test')
    add_holding(database, 'owner@example.test', 'XQA', 10, 100_000, 11_000)
    set_cash(database, 'owner@example.test', 77_777_777)

    guest = app.test_client()
    page = guest.get('/portfolio')
    response = guest.get('/api/portfolio')

    assert page.status_code == 401 and response.status_code == 401
    assert response.get_json() == {'error': 'Sign in to view your portfolio.'}
    assert b'href="/login"' in page.data
    for body in (page.data, response.data):
        assert b'XQA' not in body and b'77,777,777' not in body and b'77777777' not in body
    assert page.headers['Cache-Control'] == 'no-store'
    assert response.headers['Cache-Control'] == 'no-store'


def test_tc_us06_03_second_account_never_receives_the_first_accounts_data(app_db):
    app, database = app_db
    sign_up(app, 'owner@example.test')
    other = sign_up(app, 'other@example.test')
    add_holding(database, 'owner@example.test', 'XQA', 10, 100_000, 11_000)
    set_cash(database, 'owner@example.test', 77_777_777)
    owner_id = account_id(database, 'owner@example.test')

    honest = api(other)
    # A client-chosen account id in the query string must change nothing.
    tampered = other.get(f'/api/portfolio?account_id={owner_id}&id={owner_id}').get_json()
    assert honest == tampered
    assert honest['positions'] == []
    assert honest['cash_vnd'] == GRANT == honest['total_value_vnd']
    page = other.get(f'/portfolio?account_id={owner_id}').data
    assert b'XQA' not in page and b'77,777,777' not in page


@pytest.mark.parametrize('change', [
    'UPDATE auth_session SET revoked_at = \'2000-01-01T00:00:00Z\'',
    'UPDATE account SET status = \'disabled\'',
])
def test_tc_us06_03_revoked_session_or_disabled_account_gets_401(app_db, change):
    app, database = app_db
    client = sign_up(app, 'owner@example.test')
    assert client.get('/api/portfolio').status_code == 200
    run(database, change)

    assert client.get('/api/portfolio').status_code == 401
    assert client.get('/portfolio').status_code == 401


# --- TC-US06-04 -------------------------------------------------------------


def test_tc_us06_04_missing_quote_is_incomplete_and_never_valued_as_zero(app_db):
    app, database = app_db
    client = sign_up(app, 'owner@example.test')
    add_holding(database, 'owner@example.test', 'XQA', 100, 3_000_000, 32_000)
    add_holding(database, 'owner@example.test', 'XQB', 50, 2_500_000, None)  # no quote row

    payload = api(client)
    by_symbol = {p['symbol']: p for p in payload['positions']}
    unpriced = by_symbol['XQB']
    assert unpriced['priced'] is False
    assert unpriced['market_value_vnd'] is None and unpriced['unrealised_pnl_vnd'] is None
    assert unpriced['unrealised_pnl_percent'] is None and unpriced['price_vnd'] is None
    # Quantity and cost basis stay visible: the holding is not dropped.
    assert unpriced['quantity'] == 50 and unpriced['cost_basis_vnd'] == 2_500_000
    assert payload['valuation_complete'] is False and payload['unpriced_count'] == 1
    # The priced holding is still exact and the total omits only the unpriced one.
    assert by_symbol['XQA']['market_value_vnd'] == 3_200_000
    assert payload['holdings_value_vnd'] == 3_200_000
    assert payload['total_value_vnd'] == GRANT + 3_200_000

    page = client.get('/portfolio').data
    assert b'No quote available' in page and b'Incomplete: 1 holding without a price' in page


def test_tc_us06_04_delayed_quote_is_flagged_but_keeps_its_value(app_db):
    app, database = app_db
    client = sign_up(app, 'owner@example.test')
    add_holding(database, 'owner@example.test', 'XQA', 100, 3_000_000, 32_000,
                quoted_at=stamp(seconds_ago=2 * 3600))

    payload = api(client)
    position = only_position(payload)
    assert position['stale'] is True and position['priced'] is True
    assert position['market_value_vnd'] == 3_200_000   # delayed, not zero
    assert payload['stale_count'] == 1 and payload['unpriced_count'] == 0
    assert payload['total_value_vnd'] == GRANT + 3_200_000
    assert b'Price may be delayed' in client.get('/portfolio').data


# --- TC-US06-05 -------------------------------------------------------------


@pytest.mark.parametrize(
    'quantity,cost,price,value,pnl,percent',
    [
        pytest.param(1, 1, 1, 1, 0, '0.00', id='smallest-position-no-gain'),
        pytest.param(1, 0, 5_000, 5_000, 5_000, None, id='zero-cost-has-no-percentage'),
        pytest.param(1, 20_000, 20_001, 20_001, 1, '0.01', id='half-cent-rounds-up'),
        pytest.param(1, 20_000, 19_999, 19_999, -1, '-0.01', id='negative-half-cent-away-from-zero'),
        pytest.param(3, 10_000, 4_000, 12_000, 2_000, '20.00', id='odd-average-exact-percent'),
        pytest.param(1_000_000, 100_000_000_000, 100_001, 100_001_000_000, 1_000_000,
                     '0.00', id='large-quantity-and-value'),
    ],
)
def test_tc_us06_05_quantity_value_and_percent_boundaries(
        app_db, quantity, cost, price, value, pnl, percent):
    app, database = app_db
    client = sign_up(app, 'owner@example.test')
    add_holding(database, 'owner@example.test', 'XQA', quantity, cost, price)

    payload = api(client)
    position = only_position(payload)
    assert position['market_value_vnd'] == value
    assert position['unrealised_pnl_vnd'] == pnl
    assert position['unrealised_pnl_percent'] == percent
    assert payload['holdings_value_vnd'] == value
    assert payload['total_value_vnd'] == GRANT + value
    for number in (position['market_value_vnd'], position['unrealised_pnl_vnd'],
                   payload['total_value_vnd']):
        assert type(number) is int


# --- TC-US06-06 -------------------------------------------------------------

NOW = datetime(2026, 10, 28, 9, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize('age,stale', [
    (900, False),    # exactly 15 minutes is still current
    (901, True),     # one second older is delayed
    (-300, False),   # up to 5 minutes ahead is clock skew
    (-301, True),    # beyond that the timestamp is not trusted
])
def test_tc_us06_06_quote_age_boundary(age, stale):
    quoted_at = (NOW - timedelta(seconds=age)).strftime('%Y-%m-%dT%H:%M:%SZ')
    position = value_position(
        Position('XQA', 'XQA test company', 100, 3_000_000, 32_000, quoted_at), now=NOW
    )
    assert position.stale is stale
    assert position.priced is True and position.market_value_vnd == 3_200_000