"""Read-only SQLite queries belonging to the portfolio module.

Cash and holdings are read inside one read transaction on one read-only
connection, so a buy committed between the two SELECTs cannot produce a total
that counts the debited cash but not the new holding (US06-AC4: one snapshot).
"""

import sqlite3
from pathlib import Path

from virtutrade.portfolio.errors import AccountNotFound, PortfolioDataUnavailable
from virtutrade.portfolio.models import Position

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