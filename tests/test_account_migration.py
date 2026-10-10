"""Account-state migration contract verification for #80.

US01 needs session storage (expiry, revocation) and login counters (five
failures lock an account for 15 minutes), but the M2 schema has neither. This
file verifies the PROPOSED migration below against copies of M2 databases, so
#77 can implement it without touching live data. The SQL here is the proposal
under review, not the shipped implementation: when #77 lands it in src/, these
tests keep passing unchanged against the real migration entry point.

Every test uses pytest tmp_path. Live databases are never opened.
"""
import shutil
import sqlite3

import pytest

from virtutrade.database.schema import SCHEMA

# Proposed statements for #77 to implement (see docs/account-migration.md).
# Raw ALTER TABLE is NOT rerunnable, so the contract requires the guarded
# Python applier below: check-then-apply plus a schema-version record.
# ADD COLUMN keeps every existing row (defaults fill old accounts); the new
# table carries its own FK. No table is rebuilt, so ids are untouched.
ADD_FAILED_ATTEMPTS = (
    "ALTER TABLE account ADD COLUMN failed_attempts INTEGER NOT NULL"
    " DEFAULT 0 CHECK(failed_attempts >= 0)"
)
ADD_LOCKED_UNTIL = "ALTER TABLE account ADD COLUMN locked_until TEXT"
CREATE_AUTH_SESSION = """
CREATE TABLE IF NOT EXISTS auth_session (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES account(id),
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
)"""
TARGET_SCHEMA_VERSION = 2

NOW = "2026-06-01T00:00:00Z"
FUTURE = "2099-01-01T00:00:00Z"
PAST = "2000-01-01T00:00:00Z"

ORIGINAL_TABLES = ("instrument", "price_quote", "account", "holding", "trade",
                   "audit_event")
ACCOUNT_ORIGINAL_COLUMNS = ("id", "email", "password_hash", "role", "status",
                            "cash_vnd", "created_at")


def table_columns(connection, table):
    return [row[1] for row in connection.execute(
        f"PRAGMA table_info({table})").fetchall()]


def schema_version(connection):
    return connection.execute("PRAGMA user_version").fetchone()[0]


def apply_account_state_upgrade(connection):
    """Idempotent applier contract for #77: returns True when it changed
    anything, False when the database was already upgraded. Rolls back
    partial work on failure so reruns stay safe."""
    if schema_version(connection) >= TARGET_SCHEMA_VERSION:
        return False
    try:
        columns = set(table_columns(connection, "account"))
        if "failed_attempts" not in columns:
            connection.execute(ADD_FAILED_ATTEMPTS)
        if "locked_until" not in columns:
            connection.execute(ADD_LOCKED_UNTIL)
        connection.execute(CREATE_AUTH_SESSION)
        connection.execute(
            f"PRAGMA user_version = {TARGET_SCHEMA_VERSION}")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def build_m2_fixture(path):
    """A small stand-in for a real M2 database: seed-like rows plus one
    account with a holding and a trade, all with known ids."""
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    for number in range(1, 13):
        symbol = f"SYM{number:02d}"
        connection.execute(
            "INSERT INTO instrument(symbol, name) VALUES (?, ?)",
            (symbol, f"Test {number:02d}"),
        )
        connection.execute(
            "INSERT INTO price_quote(instrument_id, price_vnd,"
            " previous_close_vnd, quoted_at, source)"
            " VALUES (?, ?, ?, '2026-01-01T00:00:00Z', 'seed')",
            (number, 1000 * number, 990 * number),
        )
    connection.execute(
        "INSERT INTO account(email, password_hash, cash_vnd, created_at)"
        " VALUES ('a@example.com', 'hash', 100000000,"
        " '2026-01-01T00:00:00Z')"
    )
    connection.execute(
        "INSERT INTO holding(account_id, instrument_id, quantity,"
        " cost_basis_vnd) VALUES (1, 1, 200, 6000000)"
    )
    connection.execute(
        "INSERT INTO trade(account_id, instrument_id, side, quantity,"
        " fill_price_vnd, realised_pnl_vnd, executed_at)"
        " VALUES (1, 1, 'sell', 1000, 30000, 2000000,"
        " '2026-01-01T00:00:00Z')"
    )
    connection.commit()
    return connection


def snapshot_original(connection):
    """Every pre-migration user row, in original column order. New auth
    columns and tables are asserted separately, never mixed in."""
    data = {}
    for table in ORIGINAL_TABLES:
        if table == "account":
            cols = ", ".join(ACCOUNT_ORIGINAL_COLUMNS)
        else:
            cols = "*"
        data[table] = sorted(connection.execute(
            f"SELECT {cols} FROM {table}").fetchall())
    return data


def migrate_copy(copy_path):
    """The copy-first workflow: upgrade the copy and return it open."""
    connection = sqlite3.connect(copy_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        apply_account_state_upgrade(connection)
        return connection
    except Exception:
        connection.close()
        raise


def test_fresh_database_accepts_account_state_upgrade(tmp_path):
    """A fresh M2 database gains the auth storage with safe defaults and a
    recorded schema version."""
    connection = build_m2_fixture(tmp_path / "fresh.db")
    assert schema_version(connection) == 0
    assert apply_account_state_upgrade(connection) is True
    columns = set(table_columns(connection, "account"))
    assert {"failed_attempts", "locked_until"} <= columns
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert "auth_session" in tables
    row = connection.execute(
        "SELECT failed_attempts, locked_until FROM account WHERE id = 1"
    ).fetchone()
    assert row == (0, None)
    version = schema_version(connection)
    connection.close()
    assert version == TARGET_SCHEMA_VERSION


def test_upgrade_of_copied_fixture_preserves_ids_and_rows(tmp_path):
    """The core #80 guarantee: migrate a COPY and prove every id and row
    survives, including the 1..12 seed identities."""
    original = tmp_path / "m2-live-standin.db"
    connection = build_m2_fixture(original)
    before = snapshot_original(connection)
    connection.close()
    copy_path = tmp_path / "m2-copy.db"
    shutil.copy(original, copy_path)
    migrated = migrate_copy(copy_path)
    try:
        assert snapshot_original(migrated) == before
        assert [row[0] for row in migrated.execute(
            "SELECT id FROM instrument ORDER BY id")] == list(range(1, 13))
        assert migrated.execute(
            "SELECT COUNT(*) FROM price_quote").fetchone()[0] == 12
        assert migrated.execute(
            "SELECT COUNT(*) FROM auth_session").fetchone()[0] == 0
    finally:
        migrated.close()


def test_migration_rerun_is_noop(tmp_path):
    """The applier detects an upgraded database and changes nothing: second
    run returns False, rows and version are untouched, nothing raises."""
    copy_path = tmp_path / "rerun.db"
    build_m2_fixture(copy_path).close()
    first = sqlite3.connect(copy_path)
    assert apply_account_state_upgrade(first) is True
    before = snapshot_original(first)
    first.close()
    second = sqlite3.connect(copy_path)
    try:
        assert apply_account_state_upgrade(second) is False
        assert snapshot_original(second) == before
        assert schema_version(second) == TARGET_SCHEMA_VERSION
    finally:
        second.close()


def test_original_copy_untouched(tmp_path):
    """Proof of the copy-first rule: the source file keeps the old schema
    with no auth tables or columns after its copy is migrated."""
    original = tmp_path / "source.db"
    build_m2_fixture(original).close()
    copy_path = tmp_path / "work.db"
    shutil.copy(original, copy_path)
    migrate_copy(copy_path).close()
    check = sqlite3.connect(original)
    try:
        columns = set(table_columns(check, "account"))
        assert "failed_attempts" not in columns
        tables = {
            row[0]
            for row in check.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert "auth_session" not in tables
        assert schema_version(check) == 0
    finally:
        check.close()


def test_lockout_counter_contract(tmp_path):
    """Five failures plus a future deadline reads back as locked; a success
    resets both fields. This is the exact contract #77's login service uses."""
    connection = build_m2_fixture(tmp_path / "lock.db")
    apply_account_state_upgrade(connection)
    connection.execute(
        "UPDATE account SET failed_attempts = 5, locked_until = ?"
        " WHERE id = 1",
        (FUTURE,),
    )
    row = connection.execute(
        "SELECT failed_attempts, locked_until FROM account WHERE id = 1"
        " AND (locked_until IS NULL OR locked_until <= ?)",
        (NOW,),
    ).fetchone()
    assert row is None
    connection.execute(
        "UPDATE account SET failed_attempts = 0, locked_until = NULL"
        " WHERE id = 1"
    )
    row = connection.execute(
        "SELECT failed_attempts, locked_until FROM account WHERE id = 1"
    ).fetchone()
    connection.close()
    assert row == (0, None)


def test_counter_rejects_negative_attempts(tmp_path):
    """The CHECK keeps the counter meaningful even on direct writes."""
    connection = build_m2_fixture(tmp_path / "neg.db")
    apply_account_state_upgrade(connection)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "UPDATE account SET failed_attempts = -1 WHERE id = 1")
    connection.close()


def test_session_lifecycle_contract(tmp_path):
    """Insert, active lookup, revoke and expiry behave as #77 needs: logout
    and disabled-account revocation only stamp revoked_at; expiry is a time
    comparison, never a delete."""
    connection = build_m2_fixture(tmp_path / "sess.db")
    apply_account_state_upgrade(connection)
    connection.execute(
        "INSERT INTO auth_session(account_id, token_hash, created_at,"
        " expires_at, revoked_at) VALUES (1, 'tok1', ?, ?, NULL)",
        (PAST, FUTURE),
    )
    active = connection.execute(
        "SELECT id FROM auth_session WHERE revoked_at IS NULL"
        " AND expires_at > ?", (NOW,),
    ).fetchall()
    assert len(active) == 1
    connection.execute(
        "UPDATE auth_session SET revoked_at = ? WHERE token_hash = 'tok1'",
        (NOW,),
    )
    active = connection.execute(
        "SELECT id FROM auth_session WHERE revoked_at IS NULL"
        " AND expires_at > ?", (NOW,),
    ).fetchall()
    assert active == []
    connection.execute(
        "INSERT INTO auth_session(account_id, token_hash, created_at,"
        " expires_at, revoked_at) VALUES (1, 'tok2', ?, ?, NULL)",
        (PAST, PAST),
    )
    active = connection.execute(
        "SELECT id FROM auth_session WHERE revoked_at IS NULL"
        " AND expires_at > ?", (NOW,),
    ).fetchall()
    connection.close()
    assert active == []


def test_session_token_hash_unique(tmp_path):
    """Duplicate session tokens are rejected at the database level."""
    connection = build_m2_fixture(tmp_path / "uniq.db")
    apply_account_state_upgrade(connection)
    connection.execute(
        "INSERT INTO auth_session(account_id, token_hash, created_at,"
        " expires_at, revoked_at) VALUES (1, 'dup', ?, ?, NULL)",
        (PAST, FUTURE),
    )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO auth_session(account_id, token_hash, created_at,"
            " expires_at, revoked_at) VALUES (1, 'dup', ?, ?, NULL)",
            (PAST, FUTURE),
        )
    connection.close()


def test_session_rejects_unknown_account(tmp_path):
    """Sessions always reference a real account (FK, enforcement on)."""
    connection = build_m2_fixture(tmp_path / "fk.db")
    apply_account_state_upgrade(connection)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO auth_session(account_id, token_hash, created_at,"
            " expires_at, revoked_at) VALUES (9999, 'x', ?, ?, NULL)",
            (PAST, FUTURE),
        )
    connection.close()
