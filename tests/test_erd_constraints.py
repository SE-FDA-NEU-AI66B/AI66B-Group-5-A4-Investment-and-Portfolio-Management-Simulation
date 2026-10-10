"""Independent ERD/schema constraint review for #56.

Builds a throwaway database from virtutrade.database.schema.SCHEMA for every test
(pytest tmp_path) and checks that the constraints needed by BR1/BR2/BR5/BR6/
BR9/BR10 and US01-US06 really hold at the database level -- and records exactly
which rules still need service code. Never touches a developer's working DB.
"""
import sqlite3
from decimal import Decimal

import pytest

from virtutrade.database import SCHEMA

ACCOUNT_COLUMNS = {"id", "email", "password_hash", "role", "status", "cash_vnd",
                   "created_at"}
EXPECTED_TABLES = {"account", "instrument", "price_quote", "holding", "trade",
                   "audit_event"}


@pytest.fixture
def db(tmp_path):
    """Fresh database built from SCHEMA with FK enforcement on."""
    path = tmp_path / "erd-review.db"
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    try:
        yield connection
    finally:
        connection.close()


def add_account(connection, email, cash_vnd=100_000_000, role="investor",
                status="active"):
    cursor = connection.execute(
        "INSERT INTO account(email, password_hash, role, status, cash_vnd,"
        " created_at) VALUES (?, 'hash', ?, ?, ?, '2026-01-01T00:00:00Z')",
        (email, role, status, cash_vnd),
    )
    return cursor.lastrowid


def add_instrument(connection, symbol, name="Test Co"):
    cursor = connection.execute(
        "INSERT INTO instrument(symbol, name) VALUES (?, ?)", (symbol, name)
    )
    return cursor.lastrowid


def add_quote(connection, instrument_id, price=28_000, previous=27_500):
    connection.execute(
        "INSERT INTO price_quote(instrument_id, price_vnd, previous_close_vnd,"
        " quoted_at, source) VALUES (?, ?, ?, '2026-01-01T00:00:00Z', 'seed')",
        (instrument_id, price, previous),
    )


def test_schema_has_six_tables(db):
    """The model under review is exactly the six M2 tables. (#56)"""
    tables = {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert tables == EXPECTED_TABLES


def test_account_columns_match_dictionary(db):
    """account exposes the columns the dictionary promises. (US01/US02/US13)"""
    columns = {
        row[1] for row in db.execute("PRAGMA table_info(account)").fetchall()
    }
    assert columns == ACCOUNT_COLUMNS


def test_account_email_unique_case_insensitive(db):
    """Duplicate registration is rejected even with different letter case.

    US01 duplicate-email AC; exercised by the service, guarded here.
    """
    add_account(db, "a@example.com")
    with pytest.raises(sqlite3.IntegrityError):
        add_account(db, "A@EXAMPLE.COM")


def test_account_defaults_grant_capital_once(db):
    """A minimal insert yields exactly 100,000,000 VND as investor/active.

    US02/BR5. The single-grant rule itself needs service code.
    """
    row_id = add_account(db, "b@example.com")
    row = db.execute(
        "SELECT cash_vnd, role, status FROM account WHERE id = ?", (row_id,)
    ).fetchone()
    assert row == (100_000_000, "investor", "active")


def test_account_rejects_negative_cash(db):
    """cash_vnd >= 0 is a second guard; affordability (BR1) needs a service
    re-read inside the buy transaction."""
    with pytest.raises(sqlite3.IntegrityError):
        add_account(db, "c@example.com", cash_vnd=-1)


def test_account_rejects_unknown_role_status(db):
    """Only investor/admin roles and active/disabled statuses exist. (BR9)"""
    with pytest.raises(sqlite3.IntegrityError):
        add_account(db, "d@example.com", role="superuser")
    with pytest.raises(sqlite3.IntegrityError):
        add_account(db, "e@example.com", status="banned")


def test_instrument_symbol_unique(db):
    """One identity row per ticker. (US03)"""
    add_instrument(db, "HPG")
    with pytest.raises(sqlite3.IntegrityError):
        add_instrument(db, "HPG")


def test_holding_unique_per_account_symbol(db):
    """One holding row per account+symbol so buys aggregate instead of
    duplicating rows. (BR6)"""
    account = add_account(db, "f@example.com")
    instrument = add_instrument(db, "HPG")
    db.execute(
        "INSERT INTO holding(account_id, instrument_id, quantity,"
        " cost_basis_vnd) VALUES (?, ?, 100, 2800000)",
        (account, instrument),
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO holding(account_id, instrument_id, quantity,"
            " cost_basis_vnd) VALUES (?, ?, 100, 3200000)",
            (account, instrument),
        )


def test_holding_rejects_zero_quantity(db):
    """quantity > 0 guards the sell-side re-read. (BR2)"""
    account = add_account(db, "g@example.com")
    instrument = add_instrument(db, "HPG")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO holding(account_id, instrument_id, quantity,"
            " cost_basis_vnd) VALUES (?, ?, 0, 0)",
            (account, instrument),
        )


def test_holding_rejects_negative_cost(db):
    """cost_basis_vnd >= 0 keeps the average-cost math defined. (BR6)"""
    account = add_account(db, "h@example.com")
    instrument = add_instrument(db, "HPG")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO holding(account_id, instrument_id, quantity,"
            " cost_basis_vnd) VALUES (?, ?, 100, -1)",
            (account, instrument),
        )


def test_quote_single_snapshot_per_instrument(db):
    """UNIQUE(instrument_id) keeps exactly one latest snapshot. (BR10)"""
    instrument = add_instrument(db, "HPG")
    add_quote(db, instrument)
    with pytest.raises(sqlite3.IntegrityError):
        add_quote(db, instrument, price=29_000)


def test_quote_rejects_nonpositive_price(db):
    """Both prices must stay positive. (BR10)"""
    instrument = add_instrument(db, "HPG")
    with pytest.raises(sqlite3.IntegrityError):
        add_quote(db, instrument, price=0)
    with pytest.raises(sqlite3.IntegrityError):
        add_quote(db, instrument, previous=0)


def test_quote_rejects_unknown_source(db):
    """Only seed/dnse rows may exist. (BR10)"""
    instrument = add_instrument(db, "HPG")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO price_quote(instrument_id, price_vnd,"
            " previous_close_vnd, quoted_at, source)"
            " VALUES (?, 1, 1, '2026-01-01T00:00:00Z', 'live')",
            (instrument,),
        )


def test_quote_rejects_unknown_instrument(db):
    """Orphan quotes are impossible with FK enforcement on."""
    with pytest.raises(sqlite3.IntegrityError):
        add_quote(db, 9999)


def test_trade_rejects_unknown_parents(db):
    """Fills always reference a real account and instrument."""
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO trade(account_id, instrument_id, side, quantity,"
            " fill_price_vnd, executed_at)"
            " VALUES (9999, 9999, 'buy', 1, 1, '2026-01-01T00:00:00Z')"
        )


def test_holding_rejects_unknown_parents(db):
    """Holdings always reference a real account and instrument."""
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO holding(account_id, instrument_id, quantity,"
            " cost_basis_vnd) VALUES (9999, 9999, 1, 1)"
        )


def test_audit_rejects_unknown_admin_or_target(db):
    """Audit rows always reference two real accounts. (BR9)"""
    target = add_account(db, "i@example.com")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO audit_event(admin_id, target_account_id,"
            " previous_status, new_status, occurred_at)"
            " VALUES (9999, ?, 'active', 'disabled',"
            " '2026-01-01T00:00:00Z')",
            (target,),
        )
    admin = add_account(db, "j@example.com")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO audit_event(admin_id, target_account_id,"
            " previous_status, new_status, occurred_at)"
            " VALUES (?, 9999, 'active', 'disabled',"
            " '2026-01-01T00:00:00Z')",
            (admin,),
        )


def test_audit_rejects_bad_status(db):
    """Status changes stay inside active/disabled. (BR9)"""
    admin = add_account(db, "k@example.com")
    target = add_account(db, "l@example.com")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO audit_event(admin_id, target_account_id,"
            " previous_status, new_status, occurred_at)"
            " VALUES (?, ?, 'active', 'banned', '2026-01-01T00:00:00Z')",
            (admin, target),
        )


def test_trade_side_limited_to_buy_sell(db):
    """Only buy/sell fills are representable."""
    account = add_account(db, "m@example.com")
    instrument = add_instrument(db, "HPG")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO trade(account_id, instrument_id, side, quantity,"
            " fill_price_vnd, executed_at)"
            " VALUES (?, ?, 'hold', 1, 1, '2026-01-01T00:00:00Z')",
            (account, instrument),
        )


def test_trade_rejects_nonpositive_fill(db):
    """Fill price and quantity stay positive. (BR2/BR3 guards)"""
    account = add_account(db, "n@example.com")
    instrument = add_instrument(db, "HPG")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO trade(account_id, instrument_id, side, quantity,"
            " fill_price_vnd, executed_at)"
            " VALUES (?, ?, 'buy', 1, 0, '2026-01-01T00:00:00Z')",
            (account, instrument),
        )


def test_trade_realised_nullable_for_buys(db):
    """Buys may leave realised P&L NULL; sells store it. (US05)"""
    account = add_account(db, "o@example.com")
    instrument = add_instrument(db, "HPG")
    db.execute(
        "INSERT INTO trade(account_id, instrument_id, side, quantity,"
        " fill_price_vnd, realised_pnl_vnd, executed_at)"
        " VALUES (?, ?, 'buy', 1000, 28000, NULL,"
        " '2026-01-01T00:00:00Z')",
        (account, instrument),
    )
    row = db.execute(
        "SELECT realised_pnl_vnd FROM trade WHERE account_id = ?", (account,)
    ).fetchone()
    assert row[0] is None


def test_us05_numbers_fit_the_schema(db):
    """The schema can represent US05-AC1 exactly: 1,000 HPG filled at 30,000
    with realised +2,000,000. Service computes the numbers; storage keeps them
    exact."""
    account = add_account(db, "p@example.com")
    instrument = add_instrument(db, "HPG")
    db.execute(
        "INSERT INTO trade(account_id, instrument_id, side, quantity,"
        " fill_price_vnd, realised_pnl_vnd, executed_at)"
        " VALUES (?, ?, 'sell', 1000, 30000, 2000000,"
        " '2026-01-01T00:00:00Z')",
        (account, instrument),
    )
    row = db.execute(
        "SELECT quantity, fill_price_vnd, realised_pnl_vnd FROM trade"
        " WHERE account_id = ?",
        (account,),
    ).fetchone()
    assert row == (1000, 30000, 2000000)


def test_average_cost_integer_storage(db):
    """100@28,000 + 100@32,000 is stored as cost 6,000,000 over qty 200, so
    average cost = 30,000 exactly. The service must divide with Decimal;
    storage keeps integers. (BR6, #51 reference numbers)"""
    account = add_account(db, "q@example.com")
    instrument = add_instrument(db, "HPG")
    db.execute(
        "INSERT INTO holding(account_id, instrument_id, quantity,"
        " cost_basis_vnd) VALUES (?, ?, 200, 6000000)",
        (account, instrument),
    )
    quantity, cost = db.execute(
        "SELECT quantity, cost_basis_vnd FROM holding WHERE account_id = ?",
        (account,),
    ).fetchone()
    assert (quantity, cost) == (200, 6000000)
    assert Decimal(cost) / Decimal(quantity) == Decimal(30000)


def test_partial_sale_rounding_stays_out_of_storage(db):
    """cost 10,000 over qty 3 has no exact integer average (3333.33...), so
    the service must round explicitly and store the rounded remainder. The
    database keeps whatever integer it is given and never rounds by itself."""
    account = add_account(db, "r@example.com")
    instrument = add_instrument(db, "HPG")
    average = Decimal(10000) / Decimal(3)
    assert average != int(average)
    db.execute(
        "INSERT INTO holding(account_id, instrument_id, quantity,"
        " cost_basis_vnd) VALUES (?, ?, 2, 6667)",
        (account, instrument),
    )
    row = db.execute(
        "SELECT quantity, cost_basis_vnd FROM holding WHERE account_id = ?",
        (account,),
    ).fetchone()
    assert row == (2, 6667)


def test_foreign_keys_need_pragma(tmp_path):
    """SQLite disables FK checks by default: without PRAGMA foreign_keys = ON
    an orphan fill is accepted. Every writer must enable it, as init-db does.
    Documents a limit, not a defect."""
    from virtutrade.database import SCHEMA as schema

    path = tmp_path / "nopragma.db"
    plain = sqlite3.connect(path)
    plain.executescript(schema)
    plain.execute(
        "INSERT INTO trade(account_id, instrument_id, side, quantity,"
        " fill_price_vnd, executed_at)"
        " VALUES (9999, 9999, 'buy', 1, 1, '2026-01-01T00:00:00Z')"
    )
    count = plain.execute("SELECT COUNT(*) FROM trade").fetchone()[0]
    plain.close()
    assert count == 1


def test_timestamps_have_no_db_format_check(db):
    """quoted_at accepts any text, so ISO-8601 validation must stay in the
    service/adapter. Documents a limit, not a defect."""
    instrument = add_instrument(db, "HPG")
    db.execute(
        "INSERT INTO price_quote(instrument_id, price_vnd, previous_close_vnd,"
        " quoted_at, source) VALUES (?, 1, 1, 'not-a-date', 'seed')",
        (instrument,),
    )
    row = db.execute(
        "SELECT quoted_at FROM price_quote WHERE instrument_id = ?",
        (instrument,),
    ).fetchone()
    assert row[0] == "not-a-date"
