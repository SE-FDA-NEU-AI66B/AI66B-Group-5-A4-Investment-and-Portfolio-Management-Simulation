"""Read-only SQLite queries belonging to the market module."""

import sqlite3
from pathlib import Path

from virtutrade.market.errors import MarketDataUnavailable
from virtutrade.market.models import Candle, Quote

MARKET_QUERY = """SELECT i.symbol, i.name, q.price_vnd,
       CASE WHEN q.source != 'dnse' THEN q.previous_close_vnd
            ELSE i.reference_price_vnd END AS previous_close_vnd,
       i.reference_at, q.quoted_at, q.source
FROM price_quote AS q
JOIN instrument AS i ON i.id = q.instrument_id
ORDER BY i.symbol"""


class SQLiteQuoteRepository:
    """Map stored rows to quote models and hide SQLite-specific read errors."""

    def __init__(self, path, *, provider_only=False):
        self.path = path
        self.provider_only = provider_only

    def fetch_quotes(self) -> list[Quote]:
        try:
            return [Quote(**row) for row in read_market(self.path)
                    if not self.provider_only or row['source'] == 'dnse']
        except sqlite3.Error as exc:
            raise MarketDataUnavailable('The market snapshot could not be read.') from exc

    def fetch_bars(self, symbol, resolution, since) -> list[Candle]:
        try:
            return [Candle(*row) for row in read_bars(self.path, symbol, resolution, since)]
        except sqlite3.Error as exc:
            raise MarketDataUnavailable('Candle history could not be read.') from exc


BARS_QUERY = """SELECT b.bar_time, b.open_vnd, b.high_vnd, b.low_vnd, b.close_vnd, b.volume
FROM price_bar AS b
JOIN instrument AS i ON i.id = b.instrument_id
WHERE i.symbol = ? AND b.resolution = ? AND b.bar_time >= ?
ORDER BY b.bar_time"""


def read_bars(path, symbol, resolution, since):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        return connection.execute(BARS_QUERY, (symbol, resolution, since)).fetchall()
    except sqlite3.OperationalError as exc:
        # A database created before candles existed has no bars yet, not a fault.
        if 'no such table: price_bar' in str(exc):
            return []
        raise
    finally:
        connection.close()


def read_market(path):
    """A missing database must fail, rather than silently creating an empty file."""
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(MARKET_QUERY).fetchall()]
    finally:
        connection.close()
