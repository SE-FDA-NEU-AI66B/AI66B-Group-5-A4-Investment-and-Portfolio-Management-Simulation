"""Search, stock detail and their error states; no browser or network needed."""

import sqlite3
from dataclasses import replace

import pytest

from virtutrade import create_app
from virtutrade.database import init_database
from virtutrade.market.models import Quote
from virtutrade.market.service import filter_quotes, find_quote, normalize_query

HPG = Quote('HPG', 'Hoa Phat Group', 28000, 27500, '2026-09-30T02:00:00Z', 'seed')
VNM = Quote('VNM', 'Vinamilk', 68000, 69000, '2026-09-30T02:00:00Z', 'seed')


@pytest.fixture
def client(tmp_path):
    database = tmp_path / 'market.db'
    init_database(database)
    return create_app({'TESTING': True, 'DATABASE': str(database)}).test_client(), database


@pytest.fixture
def broken_client(tmp_path):
    missing = tmp_path / 'missing.db'
    return create_app({'TESTING': True, 'DATABASE': str(missing)}).test_client()


def test_filter_matches_symbol_and_company_case_insensitively():
    assert filter_quotes([HPG, VNM], 'hpg') == [HPG]
    assert filter_quotes([HPG, VNM], '  VINAMILK ') == [VNM]
    assert filter_quotes([HPG, VNM], 'zzz') == []


@pytest.mark.parametrize('query', [None, '', '   '])
def test_blank_query_keeps_every_quote(query):
    assert filter_quotes([HPG, VNM], query) == [HPG, VNM]


def test_query_is_trimmed_and_capped():
    assert normalize_query('  hpg  ') == 'hpg'
    assert len(normalize_query('x' * 500)) == 50


def test_find_quote_trims_and_uppercases():
    assert find_quote([HPG, VNM], ' hpg ') == HPG
    assert find_quote([HPG, VNM], 'XYZ') is None
    assert find_quote([replace(HPG, symbol='HPG')], None) is None


def test_search_by_symbol_filters_rows_and_keeps_text(client):
    agent, _ = client
    response = agent.get('/market?q=hpg')
    assert response.status_code == 200
    assert b'<strong>HPG</strong>' in response.data
    assert b'<strong>FPT</strong>' not in response.data
    assert b'value="hpg"' in response.data
    assert b'1 of 12 symbols' in response.data
    assert b'href="/market/HPG"' in response.data


def test_search_by_company_name(client):
    agent, _ = client
    response = agent.get('/market?q=vinamilk')
    assert b'<strong>VNM</strong>' in response.data
    assert b'<strong>HPG</strong>' not in response.data


def test_quote_list_api_filters_by_the_same_symbol_or_company_query(client):
    agent, _ = client
    response = agent.get('/api/market/quotes?q=vinamilk')
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert [quote['symbol'] for quote in response.get_json()['quotes']] == ['VNM']


def test_quote_detail_api_uses_the_stored_quote_and_reports_unknown_symbols(client):
    agent, _ = client
    response = agent.get('/api/market/quotes/hpg')
    assert response.status_code == 200
    assert response.get_json()['quote']['symbol'] == 'HPG'
    assert response.get_json()['quote']['price_vnd'] == 28000

    missing = agent.get('/api/market/quotes/XYZ')
    assert missing.status_code == 404
    assert missing.get_json()['error']['code'] == 'TICKER_NOT_FOUND'


def test_quote_detail_api_reports_a_transient_read_failure(broken_client):
    response = broken_client.get('/api/market/quotes/HPG')
    assert response.status_code == 503
    assert response.get_json()['error']['code'] == 'QUOTE_UNAVAILABLE'


def test_search_without_match_shows_empty_state_and_recovery(client):
    agent, _ = client
    response = agent.get('/market?q=XYZ')
    assert response.status_code == 200
    assert b'No stocks match "XYZ"' in response.data
    assert b'Clear search' in response.data
    assert b'value="XYZ"' in response.data


def test_search_text_is_escaped(client):
    agent, _ = client
    response = agent.get('/market?q=<script>alert(1)</script>')
    assert b'<script>alert(1)' not in response.data
    assert b'&lt;script&gt;' in response.data


def test_read_failure_keeps_search_text_and_offers_retry(broken_client):
    response = broken_client.get('/market?q=HPG')
    assert response.status_code == 503
    assert b'Market data is unavailable' in response.data
    assert b'value="HPG"' in response.data
    assert b'Try again' in response.data
    assert b'id="quote-rows"' in response.data


def test_detail_shows_price_change_time_source_and_buy_link(client):
    agent, _ = client
    response = agent.get('/market/hpg')
    assert response.status_code == 200
    assert b'Hoa Phat Group' in response.data
    assert b'28,000 VND' in response.data
    assert b'+1.82%' in response.data
    assert b'09:00:00 30/09/2026 (UTC+7)' in response.data
    assert b'Demo / seed' in response.data
    assert b'Price may be delayed' in response.data
    assert b'href="/trade?symbol=HPG"' in response.data


def test_detail_without_reference_says_reference_unavailable(client):
    agent, database = client
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE price_quote SET source = 'dnse' WHERE instrument_id = "
            "(SELECT id FROM instrument WHERE symbol = 'HPG')")
    response = agent.get('/market/HPG')
    assert response.status_code == 200
    assert b'Reference unavailable' in response.data


def test_unknown_symbol_returns_404_ticker_not_found(client):
    agent, _ = client
    response = agent.get('/market/XYZ')
    assert response.status_code == 404
    assert b'Ticker not found' in response.data
    assert b'Back to market' in response.data


def test_unknown_symbol_is_escaped(client):
    agent, _ = client
    response = agent.get('/market/%3Cimg%20src%3Dx%3E')
    assert response.status_code == 404
    assert b'<img src=x>' not in response.data


def test_detail_read_failure_returns_503_with_retry(broken_client):
    response = broken_client.get('/market/HPG')
    assert response.status_code == 503
    assert b'Market data is unavailable' in response.data
    assert b'Try again' in response.data


def test_detail_route_does_not_shadow_static_files(client):
    agent, _ = client
    assert agent.get('/market/static/market.css').status_code == 200
    assert agent.get('/market/static/market.js').status_code == 200
