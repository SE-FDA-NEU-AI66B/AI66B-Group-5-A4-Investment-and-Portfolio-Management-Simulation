"""Practice market simulator, in-process feeds and running behind a proxy."""

import random
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from virtutrade.accounts.service import mint_preauth_csrf
from virtutrade.app import create_app
from virtutrade.database import init_database
from virtutrade.feeds import start_background_feed
from virtutrade.market.history import price_history, tick_size
from virtutrade.market.repository import SQLiteQuoteRepository
from virtutrade.market.service import find_quote, market_snapshot
from virtutrade.orders.repository import order_unit_of_work
from virtutrade.orders.service import validate_quote
from virtutrade.simulation import market
from virtutrade.simulation.repository import init_demo

# Monday 2 November 2026, 10:00 Vietnam time.
NOW = datetime(2026, 11, 2, 3, 0, tzinfo=timezone.utc)
SECRET = 'live-market-test-secret'


@pytest.fixture
def demo(tmp_path):
    path = tmp_path / 'simulation.db'
    init_demo(path, now=NOW - timedelta(minutes=5))
    return path


def rows(path, sql, params=()):
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(sql, params).fetchall()


def quotes(path):
    return dict(rows(path, 'SELECT i.symbol, q.price_vnd FROM price_quote q '
                           'JOIN instrument i ON i.id = q.instrument_id'))


class Fixed(random.Random):
    """Every move is the same multiple of the step volatility."""

    def __init__(self, sigmas):
        super().__init__(1)
        self.sigmas = sigmas

    def gauss(self, mu=0.0, sigma=1.0):
        return self.sigmas * sigma


def test_step_moves_every_quote_on_the_price_step_and_records_candles(demo):
    before = quotes(demo)
    assert market.step(demo, now=NOW, rng=random.Random(7)) == 12
    after = quotes(demo)
    assert after != before
    for symbol, price in after.items():
        assert price % tick_size(price) == 0 and abs(price / before[symbol] - 1) < 0.07
    assert rows(demo, "SELECT DISTINCT source, quoted_at FROM price_quote") == [
        ('simulation', '2026-11-02T03:00:00.000000Z')]
    minute = int(NOW.timestamp())
    hpg = rows(demo, "SELECT b.resolution, b.bar_time, b.open_vnd, b.close_vnd FROM price_bar b "
                     "JOIN instrument i ON i.id = b.instrument_id WHERE i.symbol = 'HPG' "
                     "ORDER BY b.resolution")
    midnight = int(datetime(2026, 11, 2, tzinfo=timezone(timedelta(hours=7))).timestamp())
    assert hpg == [('1', minute, after['HPG'], after['HPG']),
                   ('1D', midnight, after['HPG'], after['HPG'])]


def test_steps_in_one_minute_merge_and_the_next_minute_opens_a_new_candle(demo):
    rng = random.Random(3)
    prices = []
    for offset in (0, 20, 40, 60):
        market.step(demo, now=NOW + timedelta(seconds=offset), rng=rng)
        prices.append(quotes(demo)['FPT'])
    candles = rows(demo, "SELECT b.bar_time, b.open_vnd, b.high_vnd, b.low_vnd, b.close_vnd, "
                         "b.volume FROM price_bar b JOIN instrument i ON i.id = b.instrument_id "
                         "WHERE i.symbol = 'FPT' AND b.resolution = '1' ORDER BY b.bar_time")
    first, second = candles
    assert first[1:5] == (prices[0], max(prices[:3]), min(prices[:3]), prices[2])
    assert second[0] == first[0] + 60 and second[1] == second[4] == prices[3]
    daily = rows(demo, "SELECT COUNT(*), MAX(volume) FROM price_bar WHERE resolution = '1D' "
                       "AND instrument_id = (SELECT id FROM instrument WHERE symbol = 'FPT')")
    assert daily[0][0] == 1 and daily[0][1] == first[5] + second[5]


def test_price_stays_inside_the_daily_band(demo):
    reference = dict(rows(demo, 'SELECT i.symbol, q.previous_close_vnd FROM price_quote q '
                                'JOIN instrument i ON i.id = q.instrument_id'))
    for minute in range(40):
        market.step(demo, now=NOW + timedelta(minutes=minute), rng=Fixed(10))
    for symbol, price in quotes(demo).items():
        assert price <= reference[symbol] * 1.07 and price > reference[symbol]
    for minute in range(40, 120):
        market.step(demo, now=NOW + timedelta(minutes=minute), rng=Fixed(-10))
    for symbol, price in quotes(demo).items():
        assert price >= reference[symbol] * 0.93


def test_a_new_vietnam_day_references_the_last_price(demo):
    market.step(demo, now=NOW, rng=random.Random(1))
    last = quotes(demo)
    market.step(demo, now=NOW + timedelta(days=1), rng=random.Random(2))
    reference = dict(rows(demo, 'SELECT i.symbol, q.previous_close_vnd FROM price_quote q '
                                'JOIN instrument i ON i.id = q.instrument_id'))
    assert reference == last


@pytest.mark.parametrize('source', ['seed', 'dnse'])
def test_simulator_refuses_databases_with_real_or_seed_quotes(tmp_path, source):
    path = tmp_path / 'other.db'
    init_database(path)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute('UPDATE price_quote SET source = ? WHERE id = 1', (source,))
        connection.execute("UPDATE price_quote SET source = 'simulation' WHERE id > 1")
    before = quotes(path)
    with pytest.raises(sqlite3.IntegrityError):
        market.step(path, now=NOW)
    assert quotes(path) == before and rows(path, 'SELECT COUNT(*) FROM price_bar') == [(0,)]


def test_simulated_quotes_stay_fresh_for_orders(demo):
    market.step(demo, now=NOW, rng=random.Random(4))
    with order_unit_of_work(str(demo)) as repo:
        quote = repo.quote('HPG')
    validate_quote(quote, NOW + timedelta(seconds=30))


def test_chart_uses_simulator_candles_after_an_illustrative_backfill(demo):
    reader = SQLiteQuoteRepository(str(demo))
    quote = find_quote(market_snapshot(reader, now=NOW), 'HPG')
    assert price_history(reader, quote, '15', now=NOW)[0] == 'illustrative'
    for minute in range(30):
        market.step(demo, now=NOW + timedelta(minutes=minute), rng=random.Random(minute))
    later = NOW + timedelta(minutes=30)
    quote = find_quote(market_snapshot(reader, now=later), 'HPG')
    source, candles = price_history(reader, quote, '15', now=later)
    recorded = [candle for candle in candles if candle.time >= int(NOW.timestamp())]
    assert source == 'simulation' and len(recorded) == 2
    backfill = candles[:len(candles) - len(recorded)]
    assert backfill and backfill[-1].close == recorded[0].open
    assert recorded[-1].close == quote.price_vnd


def test_run_simulator_stops_on_request_and_skips_a_busy_step(demo, monkeypatch, caplog):
    calls = []
    stop = threading.Event()

    def fake_step(path, rng):
        calls.append(path)
        if len(calls) == 1:
            raise sqlite3.OperationalError('database is locked')
        stop.set()

    monkeypatch.setattr(market, 'step', fake_step)
    market.run_simulator(demo, interval=0, stop=stop)
    assert calls == [demo, demo] and 'skipping one price step' in caplog.text


def test_background_feed_is_off_by_default_and_rejects_unknown_kinds(demo):
    app = create_app({'TESTING': True, 'DATABASE': str(demo), 'MARKET_FEED': 'off'})
    assert start_background_feed(app) is None
    app.config['MARKET_FEED'] = 'random'
    with pytest.raises(ValueError):
        start_background_feed(app)


def test_background_simulation_feed_moves_prices_then_stops(demo):
    app = create_app({'TESTING': True, 'DATABASE': str(demo), 'MARKET_FEED': 'simulation',
                      'SIMULATION_TICK_SECONDS': 0, 'QUOTE_MODE': 'simulation'})
    stop = threading.Event()
    before = rows(demo, 'SELECT quoted_at FROM price_quote LIMIT 1')
    thread = start_background_feed(app, stop=stop)
    for _ in range(200):
        if rows(demo, 'SELECT quoted_at FROM price_quote LIMIT 1') != before:
            break
        threading.Event().wait(0.01)
    stop.set()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert rows(demo, 'SELECT quoted_at FROM price_quote LIMIT 1') != before
    # The reset button would jump a running market back to fixture prices.
    assert 'id="demo-actions" class="demo-card" hidden' in app.test_client().get('/trade').text


def test_background_dnse_feed_without_credentials_stops_quietly(demo, monkeypatch, caplog):
    monkeypatch.delenv('DNSE_API_KEY', raising=False)
    monkeypatch.delenv('DNSE_API_SECRET', raising=False)
    app = create_app({'TESTING': True, 'DATABASE': str(demo), 'MARKET_FEED': 'dnse'})
    thread = start_background_feed(app)
    thread.join(timeout=5)
    assert not thread.is_alive() and 'Set DNSE_API_KEY' in caplog.text


def register(client, origin, **headers):
    return client.post('/api/accounts', json={'email': 'proxy@example.com',
                                              'password': 'correct horse battery'},
                       headers={'X-CSRF-Token': mint_preauth_csrf(SECRET), 'Origin': origin,
                                **headers})


def test_trusted_proxy_keeps_secure_cookies_and_the_origin_check(tmp_path):
    path = tmp_path / 'proxy.db'
    init_database(path)
    forwarded = {'X-Forwarded-Proto': 'https', 'X-Forwarded-Host': 'trade.example.app'}
    trusted = create_app({'TESTING': True, 'DATABASE': str(path), 'SECRET_KEY': SECRET,
                          'TRUST_PROXY': True}).test_client()
    response = register(trusted, 'https://trade.example.app', **forwarded)
    assert response.status_code == 201
    assert 'Secure' in response.headers['Set-Cookie']
    assert register(trusted, 'https://evil.example', **forwarded).status_code == 403


def test_forwarded_headers_are_ignored_unless_the_proxy_is_trusted(tmp_path):
    path = tmp_path / 'direct.db'
    init_database(path)
    direct = create_app({'TESTING': True, 'DATABASE': str(path), 'SECRET_KEY': SECRET}).test_client()
    forged = register(direct, 'https://trade.example.app', **{
        'X-Forwarded-Proto': 'https', 'X-Forwarded-Host': 'trade.example.app'})
    assert forged.status_code == 403


def test_market_page_offers_a_watchlist_and_hidden_star_buttons(tmp_path):
    path = tmp_path / 'watch.db'
    init_database(path)
    page = create_app({'TESTING': True, 'DATABASE': str(path)}).test_client().get('/market').text
    assert 'id="watchboard"' in page and 'id="watch-grid"' in page
    for symbol in ('HPG', 'FPT', 'VNM'):
        # Hidden until watchboard.js runs, so a page without JavaScript shows no dead button.
        assert (f'data-watch="{symbol}" aria-pressed="false" aria-label="Watch {symbol}" hidden') in page
    scripts = [page.index(name) for name in
               ('lightweight-charts.standalone.production.js', 'chart-kit.js', 'watchboard.js')]
    assert scripts == sorted(scripts)
    assert 'https://www.tradingview.com/' in page


def test_stock_page_offers_moving_average_toggles(tmp_path):
    path = tmp_path / 'detail.db'
    init_database(path)
    page = create_app({'TESTING': True, 'DATABASE': str(path)}).test_client().get('/market/HPG').text
    for period in (20, 50, 200):
        assert f'data-average="{period}"' in page
    assert 'id="chart-ma-summary"' in page
    assert page.index('chart-kit.js') < page.index('price-chart.js')


def test_illustrative_history_is_long_enough_for_a_200_period_average(tmp_path):
    path = tmp_path / 'long.db'
    init_database(path)
    client = create_app({'TESTING': True, 'DATABASE': str(path)}).test_client()
    for resolution in ('15', '1D'):
        assert len(client.get(f'/api/market/bars/HPG?resolution={resolution}').get_json()['bars']) >= 200


def test_public_feed_kind_starts_the_credential_free_feed(demo, monkeypatch):
    from virtutrade import feeds
    started = []
    monkeypatch.setattr(feeds, 'run_dnse_public', lambda database, stop: started.append(database))
    app = create_app({'TESTING': True, 'DATABASE': str(demo), 'MARKET_FEED': 'dnse-public'})
    start_background_feed(app).join(timeout=5)
    assert started == [str(demo)]
