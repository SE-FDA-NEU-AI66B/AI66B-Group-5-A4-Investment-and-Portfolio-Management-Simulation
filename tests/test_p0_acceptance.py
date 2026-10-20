"""#82 CI regression: every P0 journey and business-rule message, end to end.

These tests drive the same steps as `scripts/check_p0_journeys.py`, using Flask's test
client instead of a browser, so CI can run them on every pull request. Every test
uses its own database under tmp_path, registers through the real form, and trades
through the public API with the session's CSRF token. There are no auth
overrides, no provider calls and no production data.

Known gaps are marked `xfail(strict=True)` with their defect ID from
docs/acceptance-matrix.md. When a fix lands, the test passes, strict mode fails the
run, and the marker and the matrix must be updated together.
"""

import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

import pytest

from virtutrade.app import create_app
from virtutrade.simulation.repository import init_demo


@pytest.fixture
def setup(tmp_path):
    database = tmp_path / "p0.db"
    init_demo(database)
    app = create_app({"TESTING": True, "DATABASE": str(database), "QUOTE_MODE": "simulation"})
    return app, database


def form_token(client, path):
    return re.search(rb'name="csrf_token" value="([^"]+)"', client.get(path).data)[1].decode()


def register(client, email, password):
    return client.post("/register", data={
        "email": email, "password": password, "csrf_token": form_token(client, "/register")})


def login(client, email, password):
    return client.post("/login", data={
        "email": email, "password": password, "csrf_token": form_token(client, "/login")})


def alert(response):
    match = re.search(rb'role="alert">([^<]+)<', response.data)
    return match[1].decode() if match else None


def order_token(client):
    page = client.get("/trade")
    return {"X-CSRF-Token": re.search(rb'name="csrf-token" content="([^"]+)"', page.data)[1].decode()}


def preview(client, headers, side, symbol, quantity):
    return client.post("/api/orders/preview", json={
        "side": side, "symbol": symbol, "quantity": quantity}, headers=headers)


def submit(client, headers, side, symbol, quantity, quoted_at):
    return client.post(f"/api/orders/{side}", json={
        "symbol": symbol, "quantity": quantity, "expected_quote_at": quoted_at}, headers=headers)


def trade(client, headers, side, symbol, quantity):
    quoted_at = preview(client, headers, side, symbol, quantity).json["quote"]["quoted_at"]
    response = submit(client, headers, side, symbol, quantity, quoted_at)
    assert response.status_code == 201, response.json
    return response.json


def set_price(database, symbol, price_vnd):
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("UPDATE price_quote SET price_vnd = ? WHERE instrument_id ="
                           " (SELECT id FROM instrument WHERE symbol = ?)", (price_vnd, symbol))


def cash(database, email):
    with closing(sqlite3.connect(database)) as connection:
        return connection.execute("SELECT cash_vnd FROM account WHERE email = ?", (email,)).fetchone()[0]


def test_us01_register_errors_duplicate_and_lockout(setup):
    app, _ = setup
    client = app.test_client()
    password = secrets.token_urlsafe(16)
    assert alert(register(client, "not-an-email", password)) == "Enter a valid email address."
    assert alert(register(client, "new@example.test", "short")) == "Password must be 8..128 characters."
    created = register(client, "new@example.test", password)
    assert created.status_code == 302 and created.location == "/market"
    assert b"Log out" in client.get("/market").data
    other = app.test_client()
    assert alert(register(other, "NEW@example.test", password)) == "Email already in use"
    messages = [alert(login(other, "new@example.test", "wrong-password-1")) for _ in range(5)]
    assert messages[:4] == ["Invalid email or password"] * 4
    assert messages[4] == "Account locked. Try again in 900 seconds."
    assert alert(login(other, "new@example.test", password)).startswith("Account locked")


def test_us02_grant_once_and_only_trades_change_cash(setup):
    app, database = setup
    client = app.test_client()
    password = secrets.token_urlsafe(16)
    register(client, "grant@example.test", password)
    assert b"100,000,000 VND" in client.get("/market").data
    trade(client, order_token(client), "buy", "HPG", 100)
    client.post("/logout", data={"csrf_token": order_token(client)["X-CSRF-Token"]})
    login(client, "grant@example.test", password)
    assert cash(database, "grant@example.test") == 100_000_000 - 100 * 28_000


def test_us03_market_snapshot_and_delay_flag(setup):
    app, database = setup
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("UPDATE price_quote SET quoted_at = '2000-01-01T00:00:00Z' WHERE"
                           " instrument_id = (SELECT id FROM instrument WHERE symbol = 'HPG')")
    page = app.test_client().get("/market").data.decode()
    assert page.count("<tr>") >= 12
    hpg_row = page[page.index("<strong>HPG</strong>"):].split("</tr>")[0]
    assert "Price may be delayed" in hpg_row


@pytest.mark.xfail(strict=True, reason="D1: ticker search/detail not implemented (#85)")
def test_us03_unknown_ticker_search(setup):
    app, _ = setup
    response = app.test_client().get("/api/market/quotes/ZZZ")
    assert response.status_code == 404 and "Ticker not found" in response.get_data(as_text=True)


def test_us04_us10_buy_rules(setup):
    app, database = setup
    client = app.test_client()
    register(client, "buyer@example.test", secrets.token_urlsafe(16))
    headers = order_token(client)
    zero = preview(client, headers, "buy", "HPG", 0)
    assert zero.status_code == 422
    assert zero.json["error"]["message"] == "Quantity must be a whole number of at least 1 share."
    unknown = preview(client, headers, "buy", "ZZZ", 1)
    assert unknown.json["error"]["message"] == "Ticker not found. Choose a stock from Market."
    over = preview(client, headers, "buy", "HPG", 4000)
    assert over.json["can_submit"] is False
    assert over.json["warning"] == "Exceeds available balance by 12,000,000 VND. Reduce the quantity."
    estimate = preview(client, headers, "buy", "HPG", 1000)
    assert estimate.json["estimate_vnd"] == 28_000_000 and estimate.json["can_submit"] is True
    bought = trade(client, headers, "buy", "HPG", 1000)
    assert bought["cash_vnd"] == 72_000_000 and bought["holding"]["quantity"] == 1000
    fpt = preview(client, headers, "buy", "FPT", 3000)
    rejected = submit(client, headers, "buy", "FPT", 3000, fpt.json["quote"]["quoted_at"])
    assert rejected.status_code == 409
    assert rejected.json["error"]["message"].startswith(
        "Insufficient cash: this order needs 360,000,000 VND but only 72,000,000 VND is available")
    assert cash(database, "buyer@example.test") == 72_000_000


def test_us05_sell_gain_and_oversell(setup):
    app, database = setup
    client = app.test_client()
    register(client, "seller@example.test", secrets.token_urlsafe(16))
    headers = order_token(client)
    trade(client, headers, "buy", "HPG", 1000)
    set_price(database, "HPG", 30_000)
    first = trade(client, headers, "sell", "HPG", 500)
    over = preview(client, headers, "sell", "HPG", 800)
    assert over.json["can_submit"] is False
    assert over.json["warning"].startswith("You hold 500 HPG; the maximum you can sell is 500")
    second = trade(client, headers, "sell", "HPG", 500)
    assert first["trade"]["realised_pnl_vnd"] + second["trade"]["realised_pnl_vnd"] == 2_000_000
    assert second["cash_vnd"] == 72_000_000 + 30_000_000 and second["holding"] is None


@pytest.mark.xfail(strict=True, reason="D3: a quote change after preview is rejected "
                   "(409 QUOTE_CHANGED), US05-AC3 expects a fill at the submitted price")
def test_us05_quote_change_after_submit_fills_at_submitted_price(setup):
    app, database = setup
    client = app.test_client()
    register(client, "timing@example.test", secrets.token_urlsafe(16))
    headers = order_token(client)
    trade(client, headers, "buy", "HPG", 10)
    quoted_at = preview(client, headers, "sell", "HPG", 10).json["quote"]["quoted_at"]
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("UPDATE price_quote SET price_vnd = 27500, quoted_at = ? WHERE instrument_id"
                           " = (SELECT id FROM instrument WHERE symbol = 'HPG')",
                           (datetime.now(timezone.utc).isoformat(),))
    response = submit(client, headers, "sell", "HPG", 10, quoted_at)
    assert response.status_code == 201 and response.json["trade"]["fill_price_vnd"] == 28_000


def test_us06_portfolio_after_journey_and_isolation(setup):
    app, database = setup
    owner = app.test_client()
    register(owner, "owner@example.test", secrets.token_urlsafe(16))
    trade(owner, order_token(owner), "buy", "HPG", 200)
    set_price(database, "HPG", 33_000)
    payload = owner.get("/api/portfolio").json
    assert payload["positions"][0]["unrealised_pnl_vnd"] == 200 * 5_000
    assert payload["total_value_vnd"] == payload["cash_vnd"] + 200 * 33_000
    newcomer = app.test_client()
    register(newcomer, "newcomer@example.test", secrets.token_urlsafe(16))
    page = newcomer.get("/portfolio").data
    assert b"No positions yet" in page and b"HPG" not in page
    assert app.test_client().get("/api/portfolio").status_code == 401


@pytest.mark.xfail(strict=True, reason="D2: form login redirects to /market; US01-AC2 says the "
                   "user reaches their own portfolio")
def test_us01_sign_in_reaches_own_portfolio(setup):
    app, _ = setup
    client = app.test_client()
    password = secrets.token_urlsafe(16)
    register(client, "back@example.test", password)
    client.post("/logout", data={"csrf_token": order_token(client)["X-CSRF-Token"]})
    assert login(client, "back@example.test", password).location == "/portfolio"