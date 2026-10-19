"""Idempotent feature migration inside the caller's transaction.

Does not consume auth migration version 2 or change auth data.
"""

from virtutrade.database.schema import SCHEMA


def migrate_market_data(connection):
    """Upgrade the M2 seed schema atomically, preserving IDs and existing rows."""
    columns = {row[1] for row in connection.execute("PRAGMA table_info(instrument)")}
    if "reference_price_vnd" not in columns:
        connection.execute(
            "ALTER TABLE instrument ADD COLUMN reference_price_vnd "
            "INTEGER CHECK(reference_price_vnd > 0)"
        )
    if "reference_at" not in columns:
        connection.execute("ALTER TABLE instrument ADD COLUMN reference_at TEXT")
    quote_columns = list(connection.execute("PRAGMA table_info(price_quote)"))
    sql = connection.execute("SELECT sql FROM sqlite_master WHERE name='price_quote'").fetchone()[0]
    if any(row[1] == "previous_close_vnd" and row[3] for row in quote_columns) or "'simulation'" not in sql:
        # No other table references price_quote. Keep its PK, FK, UNIQUE and CHECKs.
        statement = SCHEMA.split("CREATE TABLE IF NOT EXISTS price_quote (")[1].split(
            ";"
        )[0]
        connection.execute("CREATE TABLE price_quote_upgrade (" + statement)
        connection.execute("INSERT INTO price_quote_upgrade SELECT * FROM price_quote")
        connection.execute("DROP TABLE price_quote")
        connection.execute("ALTER TABLE price_quote_upgrade RENAME TO price_quote")


    connection.execute("CREATE TABLE IF NOT EXISTS feature_migration (name TEXT PRIMARY KEY)")
    connection.execute("INSERT OR IGNORE INTO feature_migration VALUES ('dnse-reference-v1')")
    connection.execute("INSERT OR IGNORE INTO feature_migration VALUES ('simulation-source-v1')")
