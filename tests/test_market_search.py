"""US03 stored-quote search/detail acceptance checks."""

import sqlite3

from virtutrade import create_app
from virtutrade.database import init_database


def client_with_quotes(tmp_path):
    database = tmp_path / 'market.db'
    init_database(database)
    return create_app({'TESTING': True, 'DATABASE': str(database)}).test_client(), database


def test_html_search_matches_symbol_company_and_keeps_text(tmp_path):
    client, _ = client_with_quotes(tmp_path)
    response = client.get('/market?q=hoa%20phat')
    assert response.status_code == 200
    assert b'value="hoa phat"' in response.data
    assert b'>HPG<' in response.data
    assert b'>FPT<' not in response.data


def test_no_match_and_read_error_keep_search_text(tmp_path):
    client, _ = client_with_quotes(tmp_path)
    assert b'No stocks match' in client.get('/market?q=missing').data
    missing = create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'missing.db')}).test_client()
    response = missing.get('/market?q=HPG')
    assert response.status_code == 503
    assert b'value="HPG"' in response.data and b'Try again' in response.data


def test_quote_list_and_detail_json_share_stored_quote_contract(tmp_path):
    client, _ = client_with_quotes(tmp_path)
    listed = client.get('/api/market/quotes?q=vinamilk')
    assert listed.status_code == 200
    assert [quote['symbol'] for quote in listed.get_json()['quotes']] == ['VNM']
    detail = client.get('/api/market/quotes/hpg')
    assert detail.status_code == 200
    assert detail.get_json()['quote']['price_vnd'] == 28000


def test_detail_html_unknown_and_stale_states(tmp_path):
    client, database = client_with_quotes(tmp_path)
    page = client.get('/market/HPG')
    assert page.status_code == 200
    assert b'Last quote (UTC+7)' in page.data and b'Buy HPG' in page.data
    assert client.get('/market/NOPE').status_code == 404
    assert client.get('/api/market/quotes/NOPE').get_json()['error']['code'] == 'TICKER_NOT_FOUND'
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE price_quote SET quoted_at = '2020-01-01T00:00:00Z' WHERE id = 1")
    assert b'Price may be delayed' in client.get('/market/HPG').data
