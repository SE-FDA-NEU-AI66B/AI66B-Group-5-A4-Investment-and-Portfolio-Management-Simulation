"""One SQLite unit of work; services decide rules, repositories execute SQL."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from virtutrade.orders.errors import OrderError
from virtutrade.orders.models import Account, Holding, OrderQuote


class OrderRepository:
    def __init__(self, connection):
        self.connection = connection

    def account_for_session(self, session_id):
        row = self.connection.execute(
            "SELECT a.id, a.cash_vnd, a.status, s.expires_at, s.revoked_at "
            "FROM account a JOIN auth_session s ON s.account_id=a.id WHERE s.id=?",
            (session_id,),
        ).fetchone()
        return Account(*row) if row else None

    def quote(self, symbol):
        row = self.connection.execute(
            "SELECT i.id, i.symbol, q.price_vnd, q.quoted_at, q.source FROM instrument i "
            "LEFT JOIN price_quote q ON q.instrument_id=i.id WHERE i.symbol=?",
            (symbol,),
        ).fetchone()
        return OrderQuote(*row) if row else None

    def holding(self, account_id, instrument_id):
        row = self.connection.execute(
            "SELECT quantity, cost_basis_vnd FROM holding WHERE account_id=? AND instrument_id=?",
            (account_id, instrument_id),
        ).fetchone()
        return Holding(*row) if row else Holding()

    def save_buy(self, account, quote, holding, quantity, cost, timestamp):
        self.connection.execute(
            "UPDATE account SET cash_vnd=? WHERE id=?",
            (account.cash_vnd - cost, account.id),
        )
        self.connection.execute(
            "INSERT INTO holding(account_id,instrument_id,quantity,cost_basis_vnd) VALUES(?,?,?,?) "
            "ON CONFLICT(account_id,instrument_id) DO UPDATE SET "
            "quantity=excluded.quantity,cost_basis_vnd=excluded.cost_basis_vnd",
            (
                account.id,
                quote.instrument_id,
                holding.quantity + quantity,
                holding.cost_basis_vnd + cost,
            ),
        )
        cursor = self.connection.execute(
            "INSERT INTO trade(account_id,instrument_id,side,quantity,fill_price_vnd,executed_at) "
            "VALUES(?,?,'buy',?,?,?)",
            (account.id, quote.instrument_id, quantity, quote.price_vnd, timestamp),
        )
        return cursor.lastrowid


@contextmanager
def order_unit_of_work(path, *, write=False):
    connection = None
    try:
        connection = sqlite3.connect(
            Path(path).resolve().as_uri() + "?mode=rw", uri=True, timeout=3
        )
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        with connection:
            yield OrderRepository(connection)
    except sqlite3.Error as exc:
        raise OrderError(
            "SERVICE_UNAVAILABLE",
            "Trading data is temporarily unavailable. Please try again later.",
        ) from exc
    finally:
        if connection:
            connection.close()
