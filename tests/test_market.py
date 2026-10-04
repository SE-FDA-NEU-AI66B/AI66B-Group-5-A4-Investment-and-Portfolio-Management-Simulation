import sqlite3

import pytest

from virtutrade.app import create_app
from virtutrade.database import init_database


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "market.db"
    init_database(path)
    return path


def test_seed_is_repeatable_and_preserves_existing_prices(database):
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE price_quote SET price_vnd = 123456 WHERE id = 1")
    assert init_database(database) == 12
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT COUNT(*) FROM instrument").fetchone()[0] == 12
        assert (
            conn.execute("SELECT price_vnd FROM price_quote WHERE id = 1").fetchone()[0]
            == 123456
        )


def test_route_reads_database_and_keeps_changes_after_restart(database):
    app = create_app({"TESTING": True, "DATABASE": str(database)})
    response = app.test_client().get("/market")
    assert response.status_code == 200
    assert b"12 symbols" in response.data and b"28,000" in response.data
    assert b"+1.82%" in response.data  # HPG: (28000 - 27500) / 27500.
    with sqlite3.connect(database) as conn:
        conn.execute(
            "UPDATE price_quote SET price_vnd = 123456 WHERE instrument_id = "
            "(SELECT id FROM instrument WHERE symbol = ?)",
            ("HPG",),
        )
    restarted = create_app({"TESTING": True, "DATABASE": str(database)})
    assert b"123,456" in restarted.test_client().get("/market").data


def test_empty_database_and_missing_database_have_different_states(database, tmp_path):
    with sqlite3.connect(database) as conn:
        conn.execute("DELETE FROM price_quote")
    app = create_app({"TESTING": True, "DATABASE": str(database)})
    response = app.test_client().get("/market")
    assert response.status_code == 200 and b"No quotes yet" in response.data
    app.config["DATABASE"] = str(tmp_path / "missing.db")
    response = app.test_client().get("/market")
    assert (
        response.status_code == 503 and b"Market data is unavailable" in response.data
    )
    assert not (tmp_path / "missing.db").exists()


def test_seed_source_and_delay_are_visible(database):
    app = create_app({"TESTING": True, "DATABASE": str(database)})
    response = app.test_client().get("/market")
    assert b"not live DNSE quotes" in response.data
    assert b"Demo / seed" in response.data
    assert b"Price may be delayed" in response.data


def test_database_constraints_reject_invalid_quote(database):
    with sqlite3.connect(database) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE price_quote SET price_vnd = 0 WHERE id = 1")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO price_quote(instrument_id, price_vnd, previous_close_vnd, "
                "quoted_at, source) VALUES (9999, 1, 1, '2026-09-30T02:00:00Z', 'seed')"
            )
