"""Regression checks for feature packaging and per-application configuration."""

import re
import sqlite3

from virtutrade import create_app
from virtutrade.config import ROOT, load_config
from virtutrade.database import init_database


def test_market_page_and_assets_work_outside_repository(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    database = tmp_path / 'market.db'
    assert init_database(database) == 12
    client = create_app({'TESTING': True, 'DATABASE': str(database)}).test_client()

    redirect = client.get('/')
    assert redirect.status_code == 302
    assert redirect.headers['Location'] == '/market'
    response = client.get('/market')
    assert response.status_code == 200
    assert b'12 symbols' in response.data
    stylesheet = re.search(rb'<link[^>]+href="([^"]+)"', response.data)
    assert stylesheet is not None
    css = client.get(stylesheet.group(1).decode())
    assert css.status_code == 200
    assert css.mimetype == 'text/css'
    assert b'{' in css.data


def test_app_instances_do_not_share_database_configuration(tmp_path):
    clients = []
    for name, price in [('first', 123456), ('second', 654321)]:
        database = tmp_path / f'{name}.db'
        init_database(database)
        with sqlite3.connect(database) as conn:
            conn.execute('UPDATE price_quote SET price_vnd = ? WHERE id = 1', (price,))
        clients.append(create_app({'TESTING': True, 'DATABASE': str(database)}).test_client())

    first = clients[0].get('/market')
    second = clients[1].get('/market')
    assert b'123,456' in first.data and b'654,321' not in first.data
    assert b'654,321' in second.data and b'123,456' not in second.data


def test_relative_database_config_is_anchored_to_repository(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('DATABASE_PATH', 'instance/config-test.db')
    assert load_config()['DATABASE'] == str(ROOT / 'instance/config-test.db')
