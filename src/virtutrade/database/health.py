"""Read-only database probe for the /health endpoint."""

import sqlite3
from pathlib import Path


def quote_count(path):
    """Number of stored quotes; raises sqlite3.Error when the database is unusable.

    Read-only mode means a missing file fails instead of being created empty.
    """
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=2)
    try:
        return connection.execute('SELECT COUNT(*) FROM price_quote').fetchone()[0]
    finally:
        connection.close()
