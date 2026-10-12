"""Auth business rules: registration, login, logout, sessions, CSRF, lockout.

Functions take a database path plus explicit timestamps so tests stay
deterministic. Each writer opens its own connection with foreign keys on and
owns one BEGIN IMMEDIATE ... COMMIT/ROLLBACK transaction.
"""
import hashlib
import hmac
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from virtutrade.accounts import errors, repository
from virtutrade.accounts.models import Account, SessionRecord

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
MAX_FAILED_ATTEMPTS = 5
LOCK_SECONDS = 900
IDLE_SECONDS = 1800
ABSOLUTE_SECONDS = 12 * 3600
CSRF_PREAUTH_SCOPE = 'preauth-v1'
CSRF_SESSION_SCOPE = 'csrf-v1'

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def now_iso(moment=None):
    moment = moment or datetime.now(timezone.utc)
    return moment.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def _connect(db_path):
    connection = sqlite3.connect(db_path)
    connection.execute('PRAGMA foreign_keys = ON')
    connection.row_factory = sqlite3.Row
    return connection


def normalize_email(raw):
    if not isinstance(raw, str):
        raise errors.ValidationError('Email must be a string.')
    email = raw.strip().lower()
    if len(email) > 254 or EMAIL_RE.match(email) is None:
        raise errors.ValidationError('Enter a valid email address.')
    return email


def validate_password(raw):
    if not isinstance(raw, str) or not (
            PASSWORD_MIN_LENGTH <= len(raw) <= PASSWORD_MAX_LENGTH):
        raise errors.ValidationError(
            f'Password must be {PASSWORD_MIN_LENGTH}..{PASSWORD_MAX_LENGTH}'
            ' characters.')
    return raw


def token_hash(token):
    return repository.sha256_hex(token)


def mint_csrf(secret, session_id):
    payload = f'{CSRF_SESSION_SCOPE}:{session_id}'
    return hmac.new(secret.encode('utf-8'), payload.encode(),
                    hashlib.sha256).hexdigest()


def valid_csrf(secret, session_id, token):
    return isinstance(token, str) and hmac.compare_digest(
        mint_csrf(secret, session_id), token)


def _preauth_slot(moment):
    return moment.astimezone(timezone.utc).strftime('%Y-%m-%dT%H')


def mint_preauth_csrf(secret, now=None):
    now = now or datetime.now(timezone.utc)
    return _preauth_token_for_slot(secret, _preauth_slot(now))


def _preauth_token_for_slot(secret, slot):
    payload = f'{CSRF_PREAUTH_SCOPE}:{slot}'
    return hmac.new(secret.encode('utf-8'), payload.encode(),
                    hashlib.sha256).hexdigest()


def valid_preauth_csrf(secret, token, now=None):
    if not isinstance(token, str):
        return False
    now = now or datetime.now(timezone.utc)
    slots = [_preauth_slot(now),
             _preauth_slot(now - timedelta(hours=1))]
    return any(hmac.compare_digest(_preauth_token_for_slot(secret, slot),
                                   token)
               for slot in slots)


def same_origin_ok(host, origin, referer):
    """Browsers send Origin (or Referer) on POSTs; non-browser API clients
    send neither and skip this check but still need a CSRF token."""
    if not origin and not referer:
        return True
    candidate = origin or referer
    candidate_host = candidate.split('://', 1)[-1].split('/', 1)[0].lower()
    return candidate_host == (host or '').lower()


def seconds_until(locked_until_iso, now_iso_value):
    locked = datetime.fromisoformat(locked_until_iso.replace('Z', '+00:00'))
    now = datetime.fromisoformat(now_iso_value.replace('Z', '+00:00'))
    remaining = (locked - now).total_seconds()
    return max(1, int(remaining + 0.999))


def register(db_path, *, email, password, now=None):
    """Create exactly one account with its one-time grant plus its first
    session, atomically. Extra client keys are never read by callers."""
    address = normalize_email(email)
    validate_password(password)
    stamp = now_iso(now)
    secret_token = secrets.token_hex(32)
    connection = _connect(db_path)
    try:
        connection.execute('BEGIN IMMEDIATE')
        try:
            account_id = repository.create_account(
                connection, email=address,
                password_hash=generate_password_hash(password),
                created_at=stamp)
            session_id = repository.create_session(
                connection, account_id=account_id,
                token_hash=token_hash(secret_token), created_at=stamp,
                expires_at=now_iso(
                    datetime.fromisoformat(stamp.replace('Z', '+00:00'))
                    + timedelta(seconds=ABSOLUTE_SECONDS)),
                last_seen_at=stamp)
            connection.commit()
        except sqlite3.IntegrityError:
            connection.rollback()
            raise errors.EmailInUse()
        row = repository.find_account_by_id(connection, account_id)
        connection.commit()
    finally:
        connection.close()
    account = Account(id=row['id'], email=row['email'], role=row['role'],
                      cash_vnd=row['cash_vnd'])
    return account, secret_token, session_id


def authenticate(db_path, *, email, password, now=None):
    """Check credentials, lockout and status; rotate to a fresh session."""
    address = normalize_email(email)
    stamp = now_iso(now)
    now_moment = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    connection = _connect(db_path)
    try:
        connection.execute('BEGIN IMMEDIATE')
        try:
            row = repository.find_account_by_email(connection, address)
            if row is None:
                connection.rollback()
                raise errors.InvalidCredentials()
            if row['status'] != 'active':
                connection.rollback()
                raise errors.AccountDisabled()
            attempts, locked_until = repository.account_lock_state(
                connection, row['id'])
            if locked_until is not None and locked_until > stamp:
                remaining = seconds_until(locked_until, stamp)
                connection.rollback()
                raise errors.AccountLocked(remaining)
            if not check_password_hash(
                    _stored_hash(connection, row['id']), password):
                attempts = (attempts or 0) + 1
                if attempts >= MAX_FAILED_ATTEMPTS:
                    locked = now_iso(now_moment + timedelta(seconds=LOCK_SECONDS))
                    repository.set_failed_attempts(
                        connection, row['id'], attempts, locked)
                    connection.commit()
                    raise errors.AccountLocked(LOCK_SECONDS)
                repository.set_failed_attempts(
                    connection, row['id'], attempts, None)
                connection.commit()
                raise errors.InvalidCredentials()
            repository.clear_lockout(connection, row['id'])
            secret_token = secrets.token_hex(32)
            session_id = repository.create_session(
                connection, account_id=row['id'],
                token_hash=token_hash(secret_token), created_at=stamp,
                expires_at=now_iso(now_moment + timedelta(
                    seconds=ABSOLUTE_SECONDS)),
                last_seen_at=stamp)
            connection.commit()
            fresh = repository.find_account_by_id(connection, row['id'])
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
    finally:
        connection.close()
    account = Account(id=fresh['id'], email=fresh['email'], role=fresh['role'],
                      cash_vnd=fresh['cash_vnd'])
    return account, secret_token, session_id


def _stored_hash(connection, account_id):
    row = connection.execute(
        'SELECT password_hash FROM account WHERE id = ?', (account_id,)
    ).fetchone()
    return row['password_hash']


def logout(db_path, *, session_token):
    """Revoke exactly the caller's session; logout always succeeds at killing
    sessions, even for disabled accounts, so no session survives it."""
    stamp = now_iso()
    connection = _connect(db_path)
    try:
        connection.execute('BEGIN IMMEDIATE')
        try:
            row = repository.find_session_by_hash(
                connection, token_hash(session_token or ''))
            if row is None or row['revoked_at'] is not None:
                connection.rollback()
                raise errors.AuthRequired()
            repository.revoke_session(connection, row['id'], stamp)
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
    finally:
        connection.close()


def find_session(db_path, *, session_token):
    """Look up a session without any checks. Routes use it for CSRF binding
    and logout; anything authorization-related must use resolve_identity."""
    connection = _connect(db_path)
    try:
        row = repository.find_session_by_hash(
            connection, token_hash(session_token or ''))
        if row is None:
            return None
        return SessionRecord(id=row['id'], account_id=row['account_id'],
                             created_at=row['created_at'],
                             expires_at=row['expires_at'],
                             last_seen_at=row['last_seen_at'])
    finally:
        connection.close()


def resolve_with_id(db_path, *, session_token, now=None):
    """Strict gate for private routes: valid session, fresh timestamps,
    active account. Touches last_seen so idle expiry is enforced. Returns
    (Account, session id)."""
    stamp = now_iso(now)
    connection = _connect(db_path)
    try:
        connection.execute('BEGIN IMMEDIATE')
        try:
            row = repository.find_session_by_hash(
                connection, token_hash(session_token or ''))
            if row is None or row['revoked_at'] is not None:
                connection.rollback()
                raise errors.AuthRequired()
            if row['expires_at'] <= stamp or row['last_seen_at'] <= _idle_cutoff(
                    stamp):
                connection.rollback()
                raise errors.AuthRequired()
            account = repository.find_account_by_id(connection, row['account_id'])
            if account is None:
                connection.rollback()
                raise errors.AuthRequired()
            if account['status'] != 'active':
                connection.rollback()
                raise errors.AccountDisabled()
            repository.touch_session(connection, row['id'], stamp)
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
    finally:
        connection.close()
    return (Account(id=account['id'], email=account['email'],
                    role=account['role'], cash_vnd=account['cash_vnd']),
            row['id'])


def resolve_identity(db_path, *, session_token, now=None):
    account, _session = resolve_with_id(
        db_path, session_token=session_token, now=now)
    return account


def _idle_cutoff(stamp):
    moment = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    return now_iso(moment - timedelta(seconds=IDLE_SECONDS))
