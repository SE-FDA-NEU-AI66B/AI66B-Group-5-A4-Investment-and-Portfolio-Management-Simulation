"""Milestone 5 hosting checks: /health and the seeded test accounts (#153)."""

import os
import sqlite3
import subprocess
import sys

import pytest

from virtutrade.accounts import service
from virtutrade.accounts.demo import TEST_ACCOUNTS, TEST_PASSWORD, seed_test_accounts
from virtutrade.app import create_app
from virtutrade.database import init_database


@pytest.fixture
def database(tmp_path):
    path = tmp_path / 'health.db'
    init_database(path)
    return path


def client_for(path):
    return create_app({'TESTING': True, 'DATABASE': str(path)}).test_client()


def test_health_is_200_with_a_readable_database(database, monkeypatch):
    monkeypatch.setenv('RENDER_GIT_COMMIT', '0123456789abcdef')
    response = client_for(database).get('/health')
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.get_json() == {'status': 'ok', 'database': 'ok', 'quotes': 12,
                                   'mode': 'seed', 'commit': '0123456'}


def test_health_is_503_when_the_database_is_missing(tmp_path, monkeypatch):
    monkeypatch.delenv('RENDER_GIT_COMMIT', raising=False)
    monkeypatch.delenv('GIT_COMMIT', raising=False)
    missing = tmp_path / 'missing.db'
    response = client_for(missing).get('/health')
    assert response.status_code == 503
    body = response.get_json()
    assert (body['status'], body['database'], body['quotes'], body['commit']) == (
        'unavailable', 'unavailable', None, None)
    # Read-only probe: a failed check never creates an empty database file.
    assert not missing.exists()
    assert str(tmp_path) not in response.get_data(as_text=True)


def test_health_is_503_when_the_database_has_no_quotes(database):
    with sqlite3.connect(database) as connection:
        connection.execute('DELETE FROM price_quote')
    response = client_for(database).get('/health')
    assert response.status_code == 503
    assert response.get_json()['database'] == 'empty'


def test_seeding_creates_each_test_account_once_with_the_normal_grant(database):
    assert seed_test_accounts(database) == list(TEST_ACCOUNTS)
    assert seed_test_accounts(database) == []
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            'SELECT email, role, cash_vnd FROM account ORDER BY email').fetchall()
    assert rows == [(email, 'investor', 100_000_000) for email in TEST_ACCOUNTS]


def test_a_seeded_account_can_sign_in(database):
    seed_test_accounts(database)
    account, token, _session = service.authenticate(
        database, email=TEST_ACCOUNTS[0], password=TEST_PASSWORD)
    assert account.email == TEST_ACCOUNTS[0] and token


def test_seed_command_is_repeatable(database):
    env = {**os.environ, 'DATABASE_PATH': str(database)}
    command = [sys.executable, '-m', 'virtutrade', 'seed-test-accounts']
    first = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
    again = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
    assert '3 created, 0 already present' in first.stdout
    assert '0 created, 3 already present' in again.stdout
