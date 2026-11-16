"""Read-only SQLite queries belonging to the portfolio module.

Cash and holdings are read inside one read transaction on one read-only
connection, so a buy committed between the two SELECTs cannot produce a total
that counts the debited cash but not the new holding (US06-AC4: one snapshot).
"""

import sqlite3
from pathlib import Path

from virtutrade.portfolio.errors import AccountNotFound, PortfolioDataUnavailable
from virtutrade.portfolio.models import Position, Trade, TradeTotals

TRADE_COLUMNS = """t.executed_at, i.symbol, i.name, t.side, t.quantity, t.fill_price_vnd,
       t.quantity * t.fill_price_vnd AS value_vnd, t.realised_pnl_vnd"""
TOTALS_COLUMNS = """COUNT(*) AS count,
       COALESCE(SUM(CASE WHEN t.side = 'buy' THEN t.quantity * t.fill_price_vnd END), 0) AS bought_vnd,
       COALESCE(SUM(CASE WHEN t.side = 'sell' THEN t.quantity * t.fill_price_vnd END), 0) AS sold_vnd,
       COALESCE(SUM(t.realised_pnl_vnd), 0) AS realised_pnl_vnd"""
TRADED_SYMBOLS_QUERY = """SELECT DISTINCT i.symbol FROM trade AS t
JOIN instrument AS i ON i.id = t.instrument_id WHERE t.account_id = ? ORDER BY i.symbol"""

CASH_QUERY = 'SELECT cash_vnd FROM account WHERE id = ?'

# LEFT JOIN, not JOIN: a holding whose instrument has no quote row must still
# appear, with a NULL price. An inner join would hide it and quietly drop its
# cost basis out of the page.
POSITIONS_QUERY = """SELECT i.symbol, i.name, h.quantity, h.cost_basis_vnd,
       q.price_vnd, q.quoted_at
FROM holding AS h
JOIN instrument AS i ON i.id = h.instrument_id
LEFT JOIN price_quote AS q ON q.instrument_id = h.instrument_id
WHERE h.account_id = ?
ORDER BY i.symbol"""


class SQLitePortfolioRepository:
    """Map stored rows to portfolio models and hide SQLite-specific read errors."""

    def __init__(self, path):
        self.path = path

    def _connect(self):
        """Read-only URI: a missing database must fail, not be created empty."""
        return sqlite3.connect(
            Path(self.path).resolve().as_uri() + '?mode=ro', uri=True,
            isolation_level=None,
        )

    def fetch_snapshot(self, account_id: int) -> tuple[int, list[Position]]:
        """Return (cash, positions) for one account from a single snapshot."""
        try:
            connection = self._connect()
        except sqlite3.Error as exc:
            raise PortfolioDataUnavailable('The portfolio could not be read.') from exc
        try:
            connection.row_factory = sqlite3.Row
            connection.execute('BEGIN')
            cash_row = connection.execute(CASH_QUERY, (account_id,)).fetchone()
            rows = connection.execute(POSITIONS_QUERY, (account_id,)).fetchall()
            connection.execute('COMMIT')
        except sqlite3.Error as exc:
            raise PortfolioDataUnavailable('The portfolio could not be read.') from exc
        finally:
            connection.close()
        if cash_row is None:
            # A session naming a deleted account is a different failure from a
            # broken database, so the controller can answer 404 rather than 503.
            raise AccountNotFound(f'No account with id {account_id}.')
        return cash_row['cash_vnd'], [Position(**dict(row)) for row in rows]

    def fetch_trades(self, account_id: int, *, start=None, end=None, symbol=None, side=None,
                     limit=50, offset=0) -> tuple[list[Trade], TradeTotals, list[str]]:
        """Return one page of this account's trades, newest first, the totals for
        every matching trade, and the symbols the account has ever traded.

        `start`/`end` are UTC ISO strings (`end` exclusive); stored `executed_at`
        values use the same ISO form, so they compare as text.
        """
        where, params = ['t.account_id = ?'], [account_id]
        for clause, value in (('t.executed_at >= ?', start), ('t.executed_at < ?', end),
                              ('i.symbol = ?', symbol), ('t.side = ?', side)):
            if value is not None:
                where.append(clause)
                params.append(value)
        source = ('FROM trade AS t JOIN instrument AS i ON i.id = t.instrument_id WHERE '
                  + ' AND '.join(where))
        try:
            connection = self._connect()
        except sqlite3.Error as exc:
            raise PortfolioDataUnavailable('The trade history could not be read.') from exc
        try:
            connection.row_factory = sqlite3.Row
            connection.execute('BEGIN')
            rows = connection.execute(
                f'SELECT {TRADE_COLUMNS} {source} ORDER BY t.executed_at DESC, t.id DESC '
                'LIMIT ? OFFSET ?', (*params, limit, offset)).fetchall()
            totals = connection.execute(f'SELECT {TOTALS_COLUMNS} {source}', params).fetchone()
            symbols = [row['symbol'] for row in
                       connection.execute(TRADED_SYMBOLS_QUERY, (account_id,))]
            connection.execute('COMMIT')
        except sqlite3.Error as exc:
            raise PortfolioDataUnavailable('The trade history could not be read.') from exc
        finally:
            connection.close()
        return [Trade(**dict(row)) for row in rows], TradeTotals(**dict(totals)), symbols