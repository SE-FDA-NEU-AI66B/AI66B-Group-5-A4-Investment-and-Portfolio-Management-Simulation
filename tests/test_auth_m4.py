"""Sprint 4 US01/US02 boundary tests for #119.

These tests use a throwaway SQLite database and the real Flask routes. They
cover the six account-access cases and the three one-time-grant cases listed in
docs/testing.md. No developer database or private credential is used.
"""

import sqlite3
from contextlib import closing

import pytest

from virtutrade import create_app
from virtutrade.accounts import service
from virtutrade.accounts.service import mint_preauth_csrf
from virtutrade.database import init_database

SECRET = 'test-secret-119'
PASSWORD = 'Password123'
WRONG_PASSWORD = 'Wrongpass1'
GRANT = 100000000


@pytest.fixture
def client(tmp_path):
    database = tmp_path / 'auth-m4.db'
    init_database(database)
    app = create_app({
        'TESTING': True,
        'DATABASE': str(database),
        'SECRET_KEY': SECRET,
    })
    with app.test_client() as agent:
        yield agent, app, database


def post_json(agent, path, payload, *, csrf=True):
    headers = {}
    if csrf:
        headers['X-CSRF-Token'] = mint_preauth_csrf(SECRET)
    return agent.post(path, json=payload, headers=headers)


def register(agent, email='a@example.com', password=PASSWORD, **extra):
    payload = {'email': email, 'password': password}
    payload.update(extra)
    return post_json(agent, '/api/accounts', payload)


def login(agent, email='a@example.com', password=PASSWORD, **extra):
    payload = {'email': email, 'password': password}
    payload.update(extra)
    return post_json(agent, '/api/sessions', payload)


def one(db_path, sql, params=()):
    with closing(sqlite3.connect(db_path)) as connection:
        return connection.execute(sql, params).fetchone()


def count(db_path, table):
    return one(db_path, f'SELECT COUNT(*) FROM {table}')[0]


def latest_session_id(db_path):
    return one(
        db_path,
        'SELECT id FROM auth_session ORDER BY id DESC LIMIT 1',
    )[0]


def test_tc_us01_01_register_then_valid_session_opens_portfolio(client):
    agent, _app, db_path = client
    response = register(agent)

    assert response.status_code == 201
    assert response.get_json()['account']['cash_vnd'] == GRANT
    assert count(db_path, 'account') == 1
    assert count(db_path, 'auth_session') == 1
    assert agent.get('/portfolio').status_code == 200


def test_tc_us01_02_duplicate_wrong_password_and_csrf_refused_without_new_records(client):
    agent, app, db_path = client
    assert register(agent).status_code == 201
    before = (count(db_path, 'account'), count(db_path, 'auth_session'))

    duplicate = register(agent, email='A@EXAMPLE.COM')
    wrong = login(agent, password=WRONG_PASSWORD)
    missing_csrf = post_json(
        agent,
        '/api/sessions',
        {'email': 'a@example.com', 'password': PASSWORD},
        csrf=False,
    )

    assert duplicate.status_code == 409
    assert duplicate.get_json()['error']['code'] == 'EMAIL_IN_USE'
    assert wrong.status_code == 401
    assert wrong.get_json()['error']['code'] == 'INVALID_CREDENTIALS'
    assert missing_csrf.status_code == 403
    assert missing_csrf.get_json()['error']['code'] == 'CSRF_FAILED'
    assert (count(db_path, 'account'), count(db_path, 'auth_session')) == before
    assert app.test_client().get('/portfolio').status_code == 401


@pytest.mark.parametrize('length,accepted', [(7, False), (8, True)])
def test_tc_us01_03_password_minimum_boundary(client, length, accepted):
    agent, _app, db_path = client
    response = register(agent, password='x' * length)

    if accepted:
        assert response.status_code == 201
        assert count(db_path, 'account') == 1
    else:
        assert response.status_code == 422
        assert response.get_json()['error']['code'] == 'VALIDATION_ERROR'
        assert count(db_path, 'account') == 0


@pytest.mark.parametrize('length,accepted', [(128, True), (129, False)])
def test_tc_us01_04_password_maximum_boundary(client, length, accepted):
    agent, _app, db_path = client
    response = register(agent, password='x' * length)

    if accepted:
        assert response.status_code == 201
        assert count(db_path, 'account') == 1
    else:
        assert response.status_code == 422
        assert response.get_json()['error']['code'] == 'VALIDATION_ERROR'
        assert count(db_path, 'account') == 0


def test_tc_us01_05_fifth_failure_locks_and_correct_password_stays_locked(client):
    agent, _app, db_path = client
    assert register(agent).status_code == 201
    for _ in range(4):
        assert login(agent, password=WRONG_PASSWORD).status_code == 401

    fifth = login(agent, password=WRONG_PASSWORD)
    assert fifth.status_code == 429
    assert fifth.get_json()['error']['code'] == 'LOGIN_LOCKED'
    assert fifth.headers['Retry-After'] == '900'
    correct = login(agent, password=PASSWORD)
    assert correct.status_code == 429
    row = one(db_path, 'SELECT failed_attempts, locked_until'
                        ' FROM account WHERE email = ?', ('a@example.com',))
    assert row[0] == 5
    assert row[1] is not None


def test_tc_us02_01_registration_grants_exactly_once(client):
    agent, _app, db_path = client
    response = register(agent)

    assert response.status_code == 201
    assert response.get_json()['account']['cash_vnd'] == GRANT
    row = one(db_path, 'SELECT cash_vnd FROM account WHERE email = ?',
              ('a@example.com',))
    assert row[0] == GRANT
    assert count(db_path, 'account') == 1


def test_tc_us02_02_login_logout_cycles_never_regrant(client):
    agent, _app, db_path = client
    assert register(agent).status_code == 201

    for _ in range(2):
        session_id = latest_session_id(db_path)
        logout = agent.delete(
            '/api/sessions/current',
            headers={'X-CSRF-Token': service.mint_csrf(SECRET, session_id)},
        )
        assert logout.status_code == 204
        assert login(agent).status_code == 200
        assert one(db_path, 'SELECT cash_vnd FROM account WHERE email = ?',
                   ('a@example.com',))[0] == GRANT

    assert count(db_path, 'account') == 1


def test_tc_us02_03_client_supplied_balances_are_ignored(client):
    agent, _app, db_path = client

    for email, attempted in [
        ('low@example.com', GRANT - 1),
        ('high@example.com', GRANT + 1),
    ]:
        response = register(
            agent,
            email=email,
            cash_vnd=attempted,
            initial_balance=attempted,
            balance=attempted,
        )
        assert response.status_code == 201
        assert response.get_json()['account']['cash_vnd'] == GRANT
        assert one(db_path, 'SELECT cash_vnd FROM account WHERE email = ?',
                   (email,))[0] == GRANT

    assert count(db_path, 'account') == 2
