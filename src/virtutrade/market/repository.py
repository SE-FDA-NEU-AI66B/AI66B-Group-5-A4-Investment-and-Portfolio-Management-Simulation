"""Read-only SQLite queries belonging to the market module."""

import sqlite3
from pathlib import Path

from virtutrade.market.errors import MarketDataUnavailable
from virtutrade.market.models import Quote

MARKET_QUERY = """SELECT i.symbol, i.name, q.price_vnd, q.previous_close_vnd,
       q.quoted_at, q.source
FROM price_quote AS q
JOIN instrument AS i ON i.id = q.instrument_id
ORDER BY i.symbol"""


class SQLiteQuoteRepository:
    """Map stored rows to quote models and hide SQLite-specific read errors."""

    def __init__(self, path):
        self.path = path

    def fetch_quotes(self) -> list[Quote]:
        try:
            return [Quote(**row) for row in read_market(self.path)]
        except sqlite3.Error as exc:
            raise MarketDataUnavailable('The market snapshot could not be read.') from exc


def read_market(path):
    """A missing database must fail, rather than silently creating an empty file."""
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(MARKET_QUERY).fetchall()]
    finally:
        connection.close()
