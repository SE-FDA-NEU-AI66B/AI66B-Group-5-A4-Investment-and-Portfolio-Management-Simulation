"""SQLite account/session/lockout storage plus the account-state migration.

Rule: functions take an open connection and never commit; callers own the
transaction (service opens BEGIN IMMEDIATE ... COMMIT/ROLLBACK, seed.py
commits its seed loop before upgrading). Row results need
``connection.row_factory = sqlite3.Row``, set by the service that owns the
connection.
"""
import hashlib

ACCOUNT_STATE_VERSION = 2

ADD_FAILED_ATTEMPTS = (
    'ALTER TABLE account ADD COLUMN failed_attempts INTEGER NOT NULL'
    ' DEFAULT 0 CHECK(failed_attempts >= 0)'
)
ADD_LOCKED_UNTIL = 'ALTER TABLE account ADD COLUMN locked_until TEXT'
CREATE_AUTH_SESSION = """
CREATE TABLE IF NOT EXISTS auth_session (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES account(id),
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    revoked_at TEXT
)"""


def table_columns(connection, table):
    return [row[1] for row in connection.execute(
        f'PRAGMA table_info({table})').fetchall()]


def schema_version(connection):
    return connection.execute('PRAGMA user_version').fetchone()[0]


def pending_statements(connection):
    """Statements still missing, so reruns and previously interrupted
    upgrades apply only what is absent."""
    columns = set(table_columns(connection, 'account'))
    statements = []
    if 'failed_attempts' not in columns:
        statements.append(ADD_FAILED_ATTEMPTS)
    if 'locked_until' not in columns:
        statements.append(ADD_LOCKED_UNTIL)
    statements.append(CREATE_AUTH_SESSION)
    return statements


def migrate_account_state(connection):
    """Idempotent upgrade to version 2. Call with no pending writes: Python's
    sqlite3 auto-begins only before INSERT/UPDATE/DELETE, never DDL, so the
    explicit transaction below is what makes rollback real. Returns True when
    it changed anything, False when already upgraded."""
    if schema_version(connection) >= ACCOUNT_STATE_VERSION:
        return False
    connection.execute('BEGIN IMMEDIATE')
    try:
        for statement in pending_statements(connection):
            connection.execute(statement)
        connection.execute(f'PRAGMA user_version = {ACCOUNT_STATE_VERSION}')
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def sha256_hex(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def create_account(connection, *, email, password_hash, created_at):
    """Insert relying on column defaults for the one-time 100,000,000 VND
    grant. Caller transaction decides atomicity with the first session."""
    cursor = connection.execute(
        'INSERT INTO account(email, password_hash, created_at)'
        ' VALUES (?, ?, ?)',
        (email, password_hash, created_at),
    )
    return cursor.lastrowid


def find_account_by_email(connection, email):
    return connection.execute(
        'SELECT id, email, role, status, cash_vnd FROM account WHERE email = ?',
        (email,),
    ).fetchone()


def find_account_by_id(connection, account_id):
    return connection.execute(
        'SELECT id, email, role, status, cash_vnd FROM account WHERE id = ?',
        (account_id,),
    ).fetchone()


def account_lock_state(connection, account_id):
    return connection.execute(
        'SELECT failed_attempts, locked_until FROM account WHERE id = ?',
        (account_id,),
    ).fetchone()


def set_failed_attempts(connection, account_id, attempts, locked_until):
    connection.execute(
        'UPDATE account SET failed_attempts = ?, locked_until = ?'
        ' WHERE id = ?',
        (attempts, locked_until, account_id),
    )


def clear_lockout(connection, account_id):
    connection.execute(
        'UPDATE account SET failed_attempts = 0, locked_until = NULL'
        ' WHERE id = ?',
        (account_id,),
    )


def create_session(connection, *, account_id, token_hash, created_at,
                   expires_at, last_seen_at):
    cursor = connection.execute(
        'INSERT INTO auth_session(account_id, token_hash, created_at,'
        ' expires_at, last_seen_at, revoked_at)'
        ' VALUES (?, ?, ?, ?, ?, NULL)',
        (account_id, token_hash, created_at, expires_at, last_seen_at),
    )
    return cursor.lastrowid


def find_session_by_hash(connection, token_hash):
    return connection.execute(
        'SELECT id, account_id, created_at, expires_at, last_seen_at,'
        ' revoked_at FROM auth_session WHERE token_hash = ?',
        (token_hash,),
    ).fetchone()


def revoke_session(connection, session_id, now_iso):
    connection.execute(
        'UPDATE auth_session SET revoked_at = ? WHERE id = ?',
        (now_iso, session_id),
    )


def touch_session(connection, session_id, now_iso):
    connection.execute(
        'UPDATE auth_session SET last_seen_at = ? WHERE id = ?',
        (now_iso, session_id),
    )
