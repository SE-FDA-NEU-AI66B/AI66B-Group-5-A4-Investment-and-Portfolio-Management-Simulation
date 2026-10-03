"""Read-only SQLite queries belonging to the market module."""

import sqlite3
from pathlib import Path

MARKET_QUERY = """SELECT i.symbol, i.name, q.price_vnd, q.previous_close_vnd,
       q.quoted_at, q.source
FROM price_quote AS q
JOIN instrument AS i ON i.id = q.instrument_id
ORDER BY i.symbol"""


def read_market(path):
    """A missing database must fail, rather than silently creating an empty file."""
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(MARKET_QUERY).fetchall()]
    finally:
        connection.close()
