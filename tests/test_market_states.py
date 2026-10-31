"""Market read states for #125: retry and empty-state presentation."""

import re
import sqlite3

from virtutrade import create_app
from virtutrade.database import init_database


def retry_button(response):
    match = re.search(rb'<button id="retry-market"[^>]*>', response.data)
    assert match is not None
    return match[0]


def test_initial_read_failure_shows_visible_retry_and_keeps_query(tmp_path):
    database = tmp_path / "missing.db"
    response = create_app({"TESTING": True, "DATABASE": str(database)}).test_client().get(
        "/market?q=HPG"
    )

    assert response.status_code == 503
    assert b"hidden" not in retry_button(response)
    assert b'value="HPG"' in response.data
    assert b"Market data is unavailable" in response.data
    assert not database.exists()


def test_retry_is_hidden_when_quotes_load(tmp_path):
    database = tmp_path / "ok.db"
    init_database(database)

    response = create_app({"TESTING": True, "DATABASE": str(database)}).test_client().get(
        "/market"
    )

    assert response.status_code == 200
    assert b"hidden" in retry_button(response)
    assert b"HPG" in response.data
    assert b"Last quote" in response.data


def test_empty_database_and_search_miss_are_distinct_states(tmp_path):
    database = tmp_path / "ok.db"
    init_database(database)
    client = create_app({"TESTING": True, "DATABASE": str(database)}).test_client()

    missed = client.get("/market?q=zzz")
    assert missed.status_code == 200
    assert b"No stocks match" in missed.data
    assert b'value="zzz"' in missed.data

    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM price_quote")

    empty = client.get("/market")
    assert empty.status_code == 200
    assert b"No quotes yet" in empty.data
    assert b"No stocks match" not in empty.data
