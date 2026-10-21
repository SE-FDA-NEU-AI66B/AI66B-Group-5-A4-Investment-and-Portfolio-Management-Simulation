"""Auth slice tests for #77: registration, login, logout, sessions, CSRF,
lockout, ownership and the account-state migration inside init-db.

Each test uses a throwaway database; no developer database is touched.
"""
import re
import sqlite3

import pytest

from virtutrade import create_app
from virtutrade.accounts import errors, service
from virtutrade.accounts.service import mint_preauth_csrf
from virtutrade.database import init_database

SECRET = 'test-secret-12345'
PASSWORD = 'Password123'
WRONG_PASSWORD = 'Wrongpass1'
LOCK_MESSAGE = 'Account locked. Try again in 900 seconds.'


@pytest.fixture
def client(tmp_path):
    database = tmp_path / 'auth.db'
    init_database(database)
    app = create_app({'TESTING': True, 'DATABASE': str(database),
                      'SECRET_KEY': SECRET})
    with app.test_client() as agent:
        yield agent, app, database


def db_row(db_path, sql, params=()):
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(sql, params).fetchone()


def db_exec(db_path, sql, params=()):
    with sqlite3.connect(db_path) as connection:
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute(sql, params)
        connection.commit()


def post_json(agent, path, payload, token='valid'):
    headers = {}
    if token == 'valid':
        headers['X-CSRF-Token'] = mint_preauth_csrf(SECRET)
    elif token:
        headers['X-CSRF-Token'] = token
    return agent.post(path, json=payload, headers=headers)


def register(agent, email='a@example.com', password=PASSWORD, **extra):
    payload = {'email': email, 'password': password}
    payload.update(extra)
    return post_json(agent, '/api/accounts', payload)


def login(agent, email='a@example.com', password=PASSWORD, **extra):
    payload = {'email': email, 'password': password}
    payload.update(extra)
    return post_json(agent, '/api/sessions', payload)


def session_cookie(response, name='vt_session'):
    for header in response.headers.getlist('Set-Cookie'):
        if header.startswith(name + '='):
            return header.split(';', 1)[0].split('=', 1)[1]
    return None


def test_register_creates_account_with_grant_and_cookie(client):
    agent, _app, db_path = client
    response = register(agent)
    assert response.status_code == 201
    body = response.get_json()
    assert body['account']['email'] == 'a@example.com'
    assert body['account']['role'] == 'investor'
    assert body['account']['cash_vnd'] == 100000000
    assert body['redirect_to'] == '/portfolio'
    assert response.headers['Location'] == '/api/portfolio'
    assert session_cookie(response) not in (None, '')
    assert response.headers['Cache-Control'] == 'no-store'
    row = db_row(db_path, 'SELECT * FROM account WHERE email = ?',
                 ('a@example.com',))
    assert row['cash_vnd'] == 100000000


def test_register_ignores_client_role_cash_and_ids(client):
    agent, _app, _db = client
    response = register(agent, role='admin', cash_vnd=999999999, id=99)
    assert response.status_code == 201
    body = response.get_json()
    assert body['account']['role'] == 'investor'
    assert body['account']['cash_vnd'] == 100000000
    assert body['account']['id'] != 99


def test_register_duplicate_email_case_insensitive(client):
    agent, _app, db_path = client
    assert register(agent).status_code == 201
    response = register(agent, email='A@EXAMPLE.COM')
    assert response.status_code == 409
    body = response.get_json()
    assert body['error']['code'] == 'EMAIL_IN_USE'
    assert body['error']['message'] == 'Email already in use'
    count = db_row(db_path, 'SELECT COUNT(*) AS n FROM account')['n']
    assert count == 1


def test_register_invalid_input_422(client):
    agent, _app, _db = client
    bad_email = register(agent, email='not-an-email')
    assert bad_email.status_code == 422
    short = register(agent, email='b@example.com', password='short')
    assert short.status_code == 422
    assert short.get_json()['error']['code'] == 'VALIDATION_ERROR'


def test_register_wrong_content_type_415(client):
    agent, _app, _db = client
    response = agent.post('/api/accounts', data='x',
                          content_type='text/plain',
                          headers={'X-CSRF-Token': mint_preauth_csrf(SECRET)})
    assert response.status_code == 415


def test_login_success_rotates_cookie(client):
    agent, _app, _db = client
    first = session_cookie(register(agent))
    response = login(agent)
    assert response.status_code == 200
    body = response.get_json()
    assert body['account']['role'] == 'investor'
    assert body['redirect_to'] == '/portfolio'
    second = session_cookie(response)
    assert second and second != first
    assert response.headers['Cache-Control'] == 'no-store'


def test_login_wrong_password_and_unknown_email_same_401(client):
    agent, _app, _db = client
    register(agent)
    wrong = login(agent, password=WRONG_PASSWORD)
    assert wrong.status_code == 401
    unknown = login(agent, email='ghost@example.com')
    assert unknown.status_code == 401
    assert (wrong.get_json()['error']['message']
            == unknown.get_json()['error']['message']
            == 'Invalid email or password')


def test_lockout_on_fifth_failure_with_retry_after(client):
    agent, _app, _db = client
    register(agent)
    for _ in range(4):
        assert login(agent, password=WRONG_PASSWORD).status_code == 401
    locked = login(agent, password=WRONG_PASSWORD)
    assert locked.status_code == 429
    assert locked.get_json()['error']['code'] == 'LOGIN_LOCKED'
    assert locked.headers['Retry-After'] == '900'
    assert LOCK_MESSAGE in locked.get_json()['error']['message']
    still_locked = login(agent, password=PASSWORD)
    assert still_locked.status_code == 429
    remaining = still_locked.get_json()['error']['details']
    assert 890 <= remaining['retry_after_seconds'] <= 900


def test_expired_lock_resets_counter_before_retry(client):
    """Regression for the PR #93 review finding: after the 15-minute lock
    expires, one wrong password is a plain 401 (not an instant re-lock),
    and the correct password afterwards succeeds."""
    agent, _app, db_path = client
    register(agent)
    for _ in range(5):
        login(agent, password=WRONG_PASSWORD)
    db_exec(db_path,
            "UPDATE account SET locked_until = '2000-01-01T00:00:00Z'")
    retry = login(agent, password=WRONG_PASSWORD)
    assert retry.status_code == 401
    row = db_row(db_path, 'SELECT failed_attempts, locked_until'
                          ' FROM account WHERE email = ?',
                 ('a@example.com',))
    assert tuple(row) == (1, None)
    assert login(agent).status_code == 200


def test_lockout_expires_and_clears_counter(client):
    agent, _app, db_path = client
    register(agent)
    for _ in range(5):
        login(agent, password=WRONG_PASSWORD)
    db_exec(db_path,
            "UPDATE account SET locked_until = '2000-01-01T00:00:00Z'")
    response = login(agent)
    assert response.status_code == 200
    row = db_row(db_path, 'SELECT failed_attempts, locked_until'
                          ' FROM account WHERE email = ?',
                 ('a@example.com',))
    assert tuple(row) == (0, None)


def test_logout_revokes_and_expires_cookie(client):
    agent, _app, db_path = client
    register(agent)
    login(agent)
    response = agent.delete(
        '/api/sessions/current',
        headers={'X-CSRF-Token': service.mint_csrf(SECRET, _session_id(
            db_path))})
    assert response.status_code == 204
    expired = response.headers.get('Set-Cookie', '')
    assert 'Max-Age=0' in expired or 'expires=' in expired.lower()
    again = agent.delete('/api/sessions/current',
                         headers={'X-CSRF-Token': 'bogus'})
    assert again.status_code == 401


def _session_id(db_path):
    return db_row(db_path, 'SELECT id FROM auth_session ORDER BY id DESC'
                           ' LIMIT 1')['id']


def test_logout_missing_session_401(client):
    agent, _app, _db = client
    response = agent.delete('/api/sessions/current')
    assert response.status_code == 401


def test_csrf_missing_and_invalid_rejected_403(client):
    agent, _app, _db = client
    register(agent)
    missing = agent.post('/api/sessions',
                         json={'email': 'a@example.com',
                               'password': PASSWORD})
    assert missing.status_code == 403
    assert missing.get_json()['error']['code'] == 'CSRF_FAILED'
    forged = post_json(agent, '/api/sessions',
                       {'email': 'a@example.com', 'password': PASSWORD},
                       token='bogus')
    assert forged.status_code == 403


def test_cross_account_isolation(client, tmp_path):
    _agent, app, db_path = client
    agent_a = app.test_client()
    agent_b = app.test_client()
    register(agent_a, email='a@example.com')
    register(agent_b, email='b@example.com')
    login(agent_a, email='a@example.com')
    login(agent_b, email='b@example.com')
    row_b = db_row(db_path, 'SELECT id FROM auth_session WHERE account_id ='
                            ' (SELECT id FROM account WHERE email = ?)'
                            ' ORDER BY id DESC LIMIT 1',
                   ('b@example.com',))
    token_b = service.mint_csrf(SECRET, row_b['id'])
    gone = agent_a.delete('/api/sessions/current',
                          headers={'X-CSRF-Token': _csrf_of(agent_a, db_path,
                                                            'a@example.com')})
    assert gone.status_code == 204
    still_there = agent_b.delete(
        '/api/sessions/current', headers={'X-CSRF-Token': token_b})
    assert still_there.status_code == 204
    forged = app.test_client()
    forged.set_cookie('vt_session', 'bogus')
    assert forged.delete('/api/sessions/current').status_code == 401


def _csrf_of(agent, db_path, email):
    del agent
    row = db_row(db_path, 'SELECT id FROM auth_session WHERE account_id ='
                          ' (SELECT id FROM account WHERE email = ?)'
                          ' ORDER BY id DESC LIMIT 1',
                 (email,))
    return service.mint_csrf(SECRET, row['id'])


def test_disabled_account_login_403_and_session_use_403(client):
    agent, app, db_path = client
    register(agent)
    token_holder = session_cookie(login(agent))
    db_exec(db_path, "UPDATE account SET status = 'disabled'")
    denied = login(agent)
    assert denied.status_code == 403
    assert denied.get_json()['error']['code'] == 'ACCOUNT_DISABLED'
    with pytest.raises(errors.AccountDisabled):
        service.resolve_identity(db_path, session_token=token_holder)
    _ = app


def test_grant_exactly_once(client):
    agent, app, db_path = client
    register(agent)
    assert register(agent).status_code == 409
    for _ in range(2):
        assert login(agent).status_code == 200
        me = app.test_client()
        me.set_cookie('vt_session',
                      session_cookie(login(agent)) or '')
        assert me.delete('/api/sessions/current',
                         headers={'X-CSRF-Token': _csrf_of(
                             me, db_path, 'a@example.com')}).status_code == 204
    rows = db_row(db_path, 'SELECT COUNT(*) AS n, SUM(cash_vnd) AS cash'
                           ' FROM account')
    assert tuple(rows) == (1, 100000000)


def test_migration_runs_inside_initdb(tmp_path):
    from virtutrade.database import init_database
    from virtutrade.database import schema as schema_module

    assert hasattr(schema_module, 'SCHEMA')
    assert 'auth_session' not in schema_module.SCHEMA
    database = tmp_path / 'fresh.db'
    assert init_database(database) == 12
    with sqlite3.connect(database) as connection:
        assert connection.execute('PRAGMA user_version').fetchone()[0] == 2
        columns = {row[1] for row in connection.execute(
            'PRAGMA table_info(account)')}
        assert {'failed_attempts', 'locked_until'} <= columns


def test_old_database_upgrades_through_initdb(tmp_path):
    from virtutrade.database import init_database

    database = tmp_path / 'old.db'
    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA_OLD_SIX_TABLES)
        connection.execute(
            "INSERT INTO account(email, password_hash, cash_vnd, created_at)"
            " VALUES ('old@example.com', 'h', 500, '2026-01-01T00:00:00Z')")
        connection.commit()
    assert init_database(database) == 12
    with sqlite3.connect(database) as connection:
        assert connection.execute('PRAGMA user_version').fetchone()[0] == 2
        row = connection.execute(
            'SELECT email, cash_vnd, failed_attempts, locked_until'
            ' FROM account WHERE email = ?', ('old@example.com',)).fetchone()
        assert tuple(row) == ('old@example.com', 500, 0, None)
        assert connection.execute(
            'SELECT COUNT(*) FROM price_quote').fetchone()[0] == 12


SCHEMA_OLD_SIX_TABLES = """
CREATE TABLE IF NOT EXISTS account (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'investor' CHECK(role IN ('investor', 'admin')),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'disabled')),
    cash_vnd INTEGER NOT NULL DEFAULT 100000000 CHECK(cash_vnd >= 0),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS instrument (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS price_quote (
    id INTEGER PRIMARY KEY,
    instrument_id INTEGER NOT NULL UNIQUE REFERENCES instrument(id),
    price_vnd INTEGER NOT NULL CHECK(price_vnd > 0),
    previous_close_vnd INTEGER NOT NULL CHECK(previous_close_vnd > 0),
    quoted_at TEXT NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('seed', 'dnse'))
);
CREATE TABLE IF NOT EXISTS holding (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES account(id),
    instrument_id INTEGER NOT NULL REFERENCES instrument(id),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    cost_basis_vnd INTEGER NOT NULL CHECK(cost_basis_vnd >= 0),
    UNIQUE(account_id, instrument_id)
);
CREATE TABLE IF NOT EXISTS trade (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES account(id),
    instrument_id INTEGER NOT NULL REFERENCES instrument(id),
    side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    fill_price_vnd INTEGER NOT NULL CHECK(fill_price_vnd > 0),
    realised_pnl_vnd INTEGER,
    executed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_event (
    id INTEGER PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES account(id),
    target_account_id INTEGER NOT NULL REFERENCES account(id),
    previous_status TEXT NOT NULL CHECK(previous_status IN ('active', 'disabled')),
    new_status TEXT NOT NULL CHECK(new_status IN ('active', 'disabled')),
    occurred_at TEXT NOT NULL
);
"""


def test_html_pages_render_with_csrf(client):
    agent, _app, _db = client
    for path in ('/register', '/login'):
        response = agent.get(path)
        assert response.status_code == 200
        assert b'name="csrf_token"' in response.data


def test_html_form_register_redirects_to_market(client):
    agent, _app, _db = client
    token = mint_preauth_csrf(SECRET)
    response = agent.post('/register', data={
        'email': 'w@example.com', 'password': PASSWORD, 'csrf_token': token})
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/market')
    market = agent.get('/market')
    assert market.status_code == 200
    assert b'Log out' in market.data
    assert b'w@example.com' in market.data


def test_html_form_login_lands_on_portfolio_once_route_exists(client):
    agent, app, _db = client
    if not any(rule.rule == '/portfolio' and 'GET' in rule.methods
               for rule in app.url_map.iter_rules()):
        app.add_url_rule('/portfolio', 'portfolio_fixture.index',
                         lambda: 'portfolio')
    register(agent)
    response = agent.post('/login', data={
        'email': 'a@example.com', 'password': PASSWORD,
        'csrf_token': mint_preauth_csrf(SECRET)})
    assert response.status_code == 302
    assert response.headers['Location'] == '/portfolio'


def test_html_guest_nav_shows_login_register(client):
    agent, _app, _db = client
    market = agent.get('/market')
    assert b'/login' in market.data
    assert b'/register' in market.data


def test_stale_session_cookie_does_not_break_public_market_read_failure(tmp_path):
    app = create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'missing.db')})
    agent = app.test_client()
    agent.set_cookie('vt_session', 'stale-cookie')
    response = agent.get('/market?q=HPG')
    assert response.status_code == 503
    assert b'Market data is unavailable' in response.data
    assert b'Try again' in response.data


def test_html_form_error_status(client):
    agent, _app, _db = client
    register(agent)
    token = mint_preauth_csrf(SECRET)
    response = agent.post('/register', data={
        'email': 'a@example.com', 'password': PASSWORD, 'csrf_token': token})
    assert response.status_code == 409
    assert b'Email already in use' in response.data
    assert b'Sign in with this email, or register with another one.' in response.data
    assert b'id="auth-error"' in response.data
    assert b'aria-describedby="auth-error"' in response.data


def test_html_error_hint_does_not_change_the_json_error_contract(client):
    agent, _app, _db = client
    register(agent)
    html = agent.post('/login', data={
        'email': 'a@example.com', 'password': WRONG_PASSWORD,
        'csrf_token': mint_preauth_csrf(SECRET)})
    assert html.status_code == 401
    assert b'Invalid email or password' in html.data
    assert b'Check both fields and try again.' in html.data
    assert b'aria-invalid="true"' in html.data

    api = login(agent, password=WRONG_PASSWORD)
    assert api.status_code == 401
    assert api.get_json()['error'] == {
        'code': 'INVALID_CREDENTIALS', 'message': 'Invalid email or password', 'details': {}}


def test_same_origin_mismatch_rejected(client):
    agent, _app, _db = client
    register(agent)
    response = agent.post('/api/sessions',
                          json={'email': 'a@example.com',
                                'password': PASSWORD},
                          headers={'X-CSRF-Token': mint_preauth_csrf(SECRET),
                                   'Origin': 'https://evil.test'})
    assert response.status_code == 403
    assert response.get_json()['error']['code'] == 'CSRF_FAILED'


def test_orders_identity_and_csrf_callbacks(client):
    from flask import g, request

    from virtutrade.accounts.routes import (
        current_order_csrf_token,
        require_order_session,
    )

    agent, app, db_path = client
    register(agent)
    token = session_cookie(login(agent))
    row = db_row(db_path, 'SELECT id FROM auth_session ORDER BY id DESC'
                          ' LIMIT 1')
    with app.test_request_context(
            '/', headers={'Cookie': 'vt_session=' + token,
                          'X-CSRF-Token': service.mint_csrf(SECRET,
                                                             row['id'])}):
        assert require_order_session(request) == row['id']
        g.current_session_id = row['id']
        assert (current_order_csrf_token()
                == service.mint_csrf(SECRET, row['id']))
    forged = app.test_request_context(
        '/', headers={'Cookie': 'vt_session=bogus'})
    with forged, pytest.raises(errors.AuthRequired):
        require_order_session(request)


def test_empty_secret_key_falls_back_to_random(monkeypatch):
    """Shipping .env.example with an empty SECRET_KEY must never produce a
    forgeable public value: each boot mints its own random key (PR #93
    review finding)."""
    from virtutrade.config import load_config

    monkeypatch.setenv('SECRET_KEY', '')
    first = load_config()['SECRET_KEY']
    second = load_config()['SECRET_KEY']
    assert re.fullmatch(r'[0-9a-f]{64}', first)
    assert first != second
