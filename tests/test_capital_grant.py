"""One-time capital grant tests for #78 (US02).

Registration grants exactly 100,000,000 VND once and shows it in the
interface. Repeat login/logout, duplicate registration, restarts and seed
reruns never grant again, and two accounts stay isolated. Each test uses a
throwaway database.
"""
import sqlite3

from virtutrade import create_app
from virtutrade.accounts.service import mint_preauth_csrf
from virtutrade.database import init_database

SECRET = 'test-secret-12345'
PASSWORD = 'Password123'
GRANT = 100000000


def make_client(tmp_path):
    database = tmp_path / 'grant.db'
    init_database(database)
    app = create_app({'TESTING': True, 'DATABASE': str(database),
                      'SECRET_KEY': SECRET})
    return app.test_client(), app, database


def register(agent, email='a@example.com', password=PASSWORD):
    return agent.post('/api/accounts',
                      json={'email': email, 'password': password},
                      headers={'X-CSRF-Token': mint_preauth_csrf(SECRET)})


def cash_of(db_path, email):
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            'SELECT cash_vnd FROM account WHERE email = ?', (email,)).fetchone()
        return row[0] if row else None


def test_grant_shown_in_ui_after_registration(tmp_path):
    """The interface displays the granted database balance after register."""
    agent, _app, _db = make_client(tmp_path)
    token = mint_preauth_csrf(SECRET)
    response = agent.post('/register', data={
        'email': 'a@example.com', 'password': PASSWORD, 'csrf_token': token})
    assert response.status_code == 302
    market = agent.get('/market')
    assert market.status_code == 200
    assert b'100,000,000 VND' in market.data
    assert b'a@example.com' in market.data


def test_repeat_login_logout_never_regrants(tmp_path):
    """Login/logout cycles leave exactly one account with the grant."""
    agent, _app, db_path = make_client(tmp_path)
    register(agent)
    for _ in range(2):
        login = agent.post(
            '/api/sessions', json={'email': 'a@example.com',
                                   'password': PASSWORD},
            headers={'X-CSRF-Token': mint_preauth_csrf(SECRET)})
        assert login.status_code == 200
    assert cash_of(db_path, 'a@example.com') == GRANT
    with sqlite3.connect(db_path) as connection:
        count = connection.execute(
            'SELECT COUNT(*) FROM account').fetchone()[0]
    assert count == 1


def test_duplicate_registration_never_regrants(tmp_path):
    """A rejected duplicate changes neither balance nor account count."""
    agent, _app, db_path = make_client(tmp_path)
    assert register(agent).status_code == 201
    assert register(agent).status_code == 409
    assert cash_of(db_path, 'a@example.com') == GRANT
    with sqlite3.connect(db_path) as connection:
        count = connection.execute(
            'SELECT COUNT(*) FROM account').fetchone()[0]
    assert count == 1


def test_seed_rerun_never_regrants(tmp_path):
    """Re-running init-db (and restarting the app against the same file)
    preserves balances instead of granting again."""
    agent, app, db_path = make_client(tmp_path)
    register(agent)
    assert init_database(db_path) == 12
    assert cash_of(db_path, 'a@example.com') == GRANT
    fresh = app.test_client()
    response = fresh.post(
        '/api/sessions', json={'email': 'a@example.com',
                               'password': PASSWORD},
        headers={'X-CSRF-Token': mint_preauth_csrf(SECRET)})
    assert response.status_code == 200
    assert cash_of(db_path, 'a@example.com') == GRANT


def test_two_accounts_stay_isolated(tmp_path):
    """Spending from one account never touches the other account's grant,
    in the database and in the interface."""
    _agent, app, db_path = make_client(tmp_path)
    client_a = app.test_client()
    client_b = app.test_client()
    register(client_a, email='a@example.com')
    register(client_b, email='b@example.com')
    with sqlite3.connect(db_path) as connection:
        connection.execute('UPDATE account SET cash_vnd = 50000000'
                           " WHERE email = 'a@example.com'")
        connection.commit()
    assert cash_of(db_path, 'a@example.com') == 50000000
    assert cash_of(db_path, 'b@example.com') == GRANT
    assert b'50,000,000 VND' in client_a.get('/market').data
    assert b'100,000,000 VND' in client_b.get('/market').data


def test_client_selected_balance_never_overrides_the_grant(tmp_path):
    """Extra client fields cannot choose or add to the initial balance."""
    agent, _app, db_path = make_client(tmp_path)
    response = register(agent, email='c@example.com')
    assert response.status_code == 201
    assert response.json['account']['cash_vnd'] == GRANT
    extra = agent.post('/api/accounts', json={
        'email': 'd@example.com', 'password': PASSWORD,
        'cash_vnd': 1, 'initial_balance': 1, 'balance': 1,
    }, headers={'X-CSRF-Token': mint_preauth_csrf(SECRET)})
    assert extra.status_code == 201
    assert extra.json['account']['cash_vnd'] == GRANT
    assert cash_of(db_path, 'd@example.com') == GRANT
