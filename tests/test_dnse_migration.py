"""Upgrade failure atomicity and separation from the auth migration version."""

import sqlite3
from contextlib import closing

import pytest

from virtutrade.database import init_database
from virtutrade.database.migrations import migrate_market_data
from virtutrade.database.schema import SCHEMA


def legacy_schema():
    return SCHEMA.replace(
        ',\n    reference_price_vnd INTEGER CHECK(reference_price_vnd > 0),\n    reference_at TEXT', ''
    ).replace('previous_close_vnd INTEGER CHECK', 'previous_close_vnd INTEGER NOT NULL CHECK')


def test_migration_failure_rolls_back_ddl_and_preserves_auth_version(tmp_path):
    path = tmp_path / 'legacy.db'
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(legacy_schema())
        connection.execute('PRAGMA user_version = 2')
        # Force an error after the ALTERs but before quote table replacement.
        connection.execute('CREATE TABLE price_quote_upgrade (occupied INTEGER)')
        connection.commit()
        with pytest.raises(sqlite3.OperationalError), connection:
            connection.execute('BEGIN IMMEDIATE')
            migrate_market_data(connection)
        assert 'reference_at' not in {r[1] for r in connection.execute('PRAGMA table_info(instrument)')}
        assert connection.execute('PRAGMA user_version').fetchone()[0] == 2
        connection.execute('DROP TABLE price_quote_upgrade')
        connection.commit()
    init_database(path)
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute('PRAGMA user_version').fetchone()[0] == 2
        assert connection.execute('SELECT name FROM feature_migration').fetchall() == [('dnse-reference-v1',)]


def test_initial_error_page_keeps_refresh_target_for_recovery(tmp_path):
    from virtutrade.app import create_app
    client = create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'missing.db')}).test_client()
    response = client.get('/market')
    assert response.status_code == 503
    assert b'id="quote-rows"' in response.data
    assert b'id="market-error"' in response.data
    assert client.get('/market/static/market.js').status_code == 200


def test_worker_cannot_overwrite_a_future_simulation_database(tmp_path):
    from virtutrade.dnse.repository import write_dnse_event
    from virtutrade.dnse.worker import Event
    path = tmp_path / 'simulation.db'
    init_database(path)
    with closing(sqlite3.connect(path)) as connection, connection:
        # Stand in for the source enum migration proposed in #75.
        connection.execute('PRAGMA ignore_check_constraints = ON')
        connection.execute("UPDATE price_quote SET source='simulation'")
    with pytest.raises(sqlite3.IntegrityError, match='simulation'):
        write_dnse_event(path, Event('sd', 'HPG', 100, '2099-01-01T00:00:00.000000000Z'))
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute('SELECT reference_at FROM instrument WHERE symbol=?', ('HPG',)).fetchone()[0] is None
        assert connection.execute("SELECT COUNT(*) FROM price_quote WHERE source='simulation'").fetchone()[0] == 12
