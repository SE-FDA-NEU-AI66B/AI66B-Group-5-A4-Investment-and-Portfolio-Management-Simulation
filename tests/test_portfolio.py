"""US06 portfolio against real storage, real sessions and real orders.

`tests/test_portfolio_valuation.py` covers the arithmetic with an in-memory
reader. This file covers what only the integrated app can show: identity from
a registered session, the LEFT JOIN read path, one snapshot per request,
results after real buy and sell orders, and the two-second response budget.

Every test builds its own database under tmp_path. No live database is opened.
"""

import re
import secrets
import sqlite3
import time
from contextlib import closing

import pytest

from virtutrade.app import create_app
from virtutrade.portfolio.errors import AccountNotFound, PortfolioDataUnavailable
from virtutrade.portfolio.repository import SQLitePortfolioRepository
from virtutrade.simulation.repository import init_demo


@pytest.fixture
def setup(tmp_path):
    database = tmp_path / "portfolio.db"
    init_demo(database)
    app = create_app({"TESTING": True, "DATABASE": str(database),
                      "QUOTE_MODE": "simulation"})
    return app, database


def register(client, email="owner@example.test"):
    """Register through the real form; return the session-bound CSRF token."""
    page = client.get("/register")
    token = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)[1].decode()
    response = client.post("/register", data={
        "email": email, "password": secrets.token_urlsafe(16), "csrf_token": token,
    })
    assert response.status_code == 302
    trade = client.get("/trade?symbol=HPG")
    return re.search(rb'name="csrf-token" content="([^"]+)"', trade.data)[1].decode()


def order(client, token, side, quantity, symbol="HPG"):
    """Preview then confirm a real order through the public API."""
    headers = {"X-CSRF-Token": token}
    preview = client.post("/api/orders/preview", json={
        "side": side, "symbol": symbol, "quantity": quantity,
    }, headers=headers)
    assert preview.status_code == 200, preview.json
    result = client.post(f"/api/orders/{side}", json={
        "symbol": symbol, "quantity": quantity,
        "expected_quote_at": preview.json["quote"]["quoted_at"],
    }, headers=headers)
    assert result.status_code == 201, result.json
    return result.json


def sql(database, statement, params=()):
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(statement, params)


def set_price(database, price_vnd, symbol="HPG"):
    """Change the reference price; the quote timestamp stays fresh."""
    sql(database, "UPDATE price_quote SET price_vnd=? WHERE instrument_id="
                  "(SELECT id FROM instrument WHERE symbol=?)", (price_vnd, symbol))


# --- US06-AC2: reference numbers -------------------------------------------


def test_us06_reference_numbers_through_real_buys(setup):
    """100 @ 28,000 + 100 @ 32,000 bought through the order API, quoted at
    33,000: 200 shares, 30,000 average, 6,600,000 value, +600,000, +10.00%."""
    app, database = setup
    client = app.test_client()
    token = register(client)
    set_price(database, 28_000)
    order(client, token, "buy", 100)
    set_price(database, 32_000)
    order(client, token, "buy", 100)
    set_price(database, 33_000)

    payload = client.get("/api/portfolio").json
    hpg = payload["positions"][0]
    assert hpg["quantity"] == 200 and hpg["average_cost_vnd"] == "30000"
    assert hpg["market_value_vnd"] == 6_600_000
    assert hpg["unrealised_pnl_vnd"] == 600_000
    assert hpg["unrealised_pnl_percent"] == "10.00"
    assert payload["cash_vnd"] == 94_000_000
    assert payload["total_value_vnd"] == 100_600_000

    page = client.get("/portfolio").data
    assert b"6,600,000" in page and b"+10.00%" in page and b"30,000.00" in page


def test_us06_total_with_forty_million_cash(setup):
    """The AC's worked total: 200 HPG at 33,000 plus 40,000,000 cash."""
    app, database = setup
    client = app.test_client()
    token = register(client)
    set_price(database, 30_000)
    order(client, token, "buy", 200)
    sql(database, "UPDATE account SET cash_vnd=40000000")
    set_price(database, 33_000)

    payload = client.get("/api/portfolio").json
    assert payload["total_value_vnd"] == 46_600_000
    assert b"46,600,000" in client.get("/portfolio").data


# --- Results after real buy and sell (US06-AC5) -----------------------------


def test_partial_and_full_sale_through_the_order_api(setup):
    app, database = setup
    client = app.test_client()
    token = register(client)
    set_price(database, 28_000)
    order(client, token, "buy", 1000)
    set_price(database, 30_000)

    order(client, token, "sell", 400)
    payload = client.get("/api/portfolio").json
    assert payload["positions"][0]["quantity"] == 600
    assert payload["positions"][0]["cost_basis_vnd"] == 16_800_000
    assert payload["cash_vnd"] == 72_000_000 + 12_000_000

    order(client, token, "sell", 600)
    payload = client.get("/api/portfolio").json
    assert payload["positions"] == []
    assert payload["cash_vnd"] == 102_000_000  # +2,000,000 realised (US05-AC1)
    assert payload["total_value_vnd"] == 102_000_000
    assert b"No positions yet" in client.get("/portfolio").data


# --- Empty portfolio (US06-AC3) ---------------------------------------------


def test_new_account_shows_no_positions_and_cash_only(setup):
    app, _ = setup
    client = app.test_client()
    register(client)
    payload = client.get("/api/portfolio").json
    assert payload["positions"] == []
    assert payload["total_value_vnd"] == payload["cash_vnd"] == 100_000_000

    page = client.get("/portfolio").data
    assert b"No positions yet" in page
    assert b"Browse the market" in page and b'href="/market"' in page


# --- Ownership and sessions -------------------------------------------------


def test_second_account_never_sees_the_first_accounts_holdings(setup):
    app, _ = setup
    owner = app.test_client()
    order(owner, register(owner, "owner@example.test"), "buy", 500)

    other = app.test_client()
    register(other, "other@example.test")
    payload = other.get("/api/portfolio").json
    assert payload["positions"] == []
    assert payload["cash_vnd"] == 100_000_000
    assert b"HPG" not in other.get("/portfolio").data.split(b"<main>")[1]


def test_account_id_in_the_request_is_ignored(setup):
    """Identity comes from the session only; query strings change nothing."""
    app, _ = setup
    owner = app.test_client()
    order(owner, register(owner, "owner@example.test"), "buy", 500)
    other = app.test_client()
    register(other, "other@example.test")

    honest = other.get("/api/portfolio").json
    tampered = other.get("/api/portfolio?account_id=1&account=1&id=1").json
    assert honest == tampered and honest["positions"] == []


@pytest.mark.parametrize("change", [
    None,  # guest: no cookie at all
    "UPDATE auth_session SET revoked_at='2000-01-01T00:00:00Z'",
    "UPDATE auth_session SET expires_at='2000-01-01T00:00:00Z'",
    "UPDATE auth_session SET last_seen_at='2000-01-01T00:00:00Z'",
    "UPDATE account SET status='disabled'",
])
def test_without_a_valid_session_both_surfaces_answer_401(setup, change):
    app, database = setup
    client = app.test_client()
    register(client)
    if change is None:
        client = app.test_client()
    else:
        sql(database, change)

    page = client.get("/portfolio")
    api = client.get("/api/portfolio")
    assert page.status_code == 401 and api.status_code == 401
    assert b'href="/login"' in page.data
    assert api.json == {"error": "Sign in to view your portfolio."}
    assert b"100,000,000" not in page.data


def test_private_responses_are_never_cached(setup):
    app, _ = setup
    client = app.test_client()
    register(client)
    for path in ("/portfolio", "/api/portfolio"):
        assert client.get(path).headers["Cache-Control"] == "no-store"
    guest = app.test_client()
    assert guest.get("/api/portfolio").headers["Cache-Control"] == "no-store"


# --- Delayed and missing quotes (US06-AC4) ----------------------------------


def test_delayed_quote_is_valued_and_flagged(setup):
    app, database = setup
    client = app.test_client()
    order(client, register(client), "buy", 100)
    sql(database, "UPDATE price_quote SET quoted_at='2026-01-01T00:00:00Z'")

    payload = client.get("/api/portfolio").json
    assert payload["positions"][0]["stale"] is True
    assert payload["positions"][0]["market_value_vnd"] == 2_800_000
    assert payload["stale_count"] == 1
    assert b"Price may be delayed" in client.get("/portfolio").data


def test_holding_without_a_quote_survives_and_is_not_zero_valued(setup):
    """A LEFT JOIN keeps the row; an inner join would drop the holding and its
    cost basis off the page, and a zero price would understate the total."""
    app, database = setup
    client = app.test_client()
    order(client, register(client), "buy", 100)
    sql(database, "PRAGMA foreign_keys=OFF")
    sql(database, "DELETE FROM price_quote WHERE instrument_id="
                  "(SELECT id FROM instrument WHERE symbol='HPG')")

    payload = client.get("/api/portfolio").json
    hpg = payload["positions"][0]
    assert hpg["symbol"] == "HPG" and hpg["quantity"] == 100
    assert hpg["cost_basis_vnd"] == 2_800_000
    assert hpg["priced"] is False and hpg["market_value_vnd"] is None
    assert payload["total_value_vnd"] == payload["cash_vnd"] == 97_200_000
    assert payload["valuation_complete"] is False
    assert b"No quote available" in client.get("/portfolio").data


# --- Repository guarantees --------------------------------------------------


def test_repository_does_not_create_a_missing_database(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(PortfolioDataUnavailable) as error:
        SQLitePortfolioRepository(path).fetch_snapshot(1)
    assert isinstance(error.value.__cause__, sqlite3.Error)
    assert not path.exists()


def test_repository_connection_cannot_write(setup):
    _, database = setup
    connection = SQLitePortfolioRepository(database)._connect()
    try:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("UPDATE account SET cash_vnd=0")
    finally:
        connection.close()


def test_unknown_account_is_account_not_found(setup):
    _, database = setup
    with pytest.raises(AccountNotFound):
        SQLitePortfolioRepository(database).fetch_snapshot(999_999)


def test_storage_failure_is_503_without_internal_detail(setup):
    app, _ = setup
    client = app.test_client()
    register(client)

    class Broken:
        def fetch_snapshot(self, account_id):
            raise PortfolioDataUnavailable("internal provider details")

    app.extensions["portfolio_reader_factory"] = Broken
    page, api = client.get("/portfolio"), client.get("/api/portfolio")
    assert page.status_code == 503 and api.status_code == 503
    assert b"internal provider details" not in page.data + api.data
    assert client.get("/market").status_code == 200  # other pages unaffected


# --- Navigation (US06-AC1) --------------------------------------------------


def test_navigation_reaches_market_buy_and_sell(setup):
    app, _ = setup
    client = app.test_client()
    order(client, register(client), "buy", 100)
    page = client.get("/portfolio").data
    assert b'href="/market"' in page and b'href="/trade"' in page
    assert b'href="/trade?side=sell&amp;symbol=HPG"' in page
    assert b'href="/portfolio"' in client.get("/market").data
    assert b'href="/portfolio"' in client.get("/trade").data


# --- Two-second budget (US06-AC5) -------------------------------------------


def test_response_time_against_the_two_second_target(setup, capsys):
    """Twelve holdings, well beyond the demo's size, timed over five loads of
    each surface. The worst sample is printed so the PR quotes a measurement."""
    app, database = setup
    client = app.test_client()
    token = register(client)
    with closing(sqlite3.connect(database)) as connection:
        symbols = [row[0] for row in connection.execute(
            "SELECT i.symbol FROM instrument i JOIN price_quote q"
            " ON q.instrument_id=i.id ORDER BY i.symbol LIMIT 12")]
    for symbol in symbols:
        order(client, token, "buy", 10, symbol=symbol)

    samples = []
    for path in ("/portfolio", "/api/portfolio") * 5:
        start = time.perf_counter()
        response = client.get(path)
        samples.append(time.perf_counter() - start)
        assert response.status_code == 200
    worst = max(samples)
    with capsys.disabled():
        print(f"\n/portfolio + /api/portfolio, {len(symbols)} holdings: "
              f"worst of {len(samples)} = {worst * 1000:.1f} ms (budget 2000 ms)")
    assert len(symbols) == 12
    assert worst < 2.0