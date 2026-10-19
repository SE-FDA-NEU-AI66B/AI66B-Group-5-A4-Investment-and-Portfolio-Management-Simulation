"""Real registration/session/CSRF integration against an isolated simulation DB."""

import re
import secrets
import sqlite3
from contextlib import closing

import pytest

from virtutrade.app import create_app
from virtutrade.database import init_database
from virtutrade.simulation.repository import init_demo


@pytest.fixture
def setup(tmp_path):
    database = tmp_path / "simulation.db"
    init_demo(database)
    app = create_app({"TESTING": True, "DATABASE": str(database),
                      "QUOTE_MODE": "simulation"})
    return app, database


def register(client, email="buyer@example.test"):
    page = client.get("/register")
    token = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)[1].decode()
    response = client.post("/register", data={
        "email": email, "password": secrets.token_urlsafe(16), "csrf_token": token,
    })
    assert response.status_code == 302 and response.location == "/market"
    trade = client.get("/trade?symbol=HPG")
    return re.search(rb'name="csrf-token" content="([^"]+)"', trade.data)[1].decode()


def financial_rows(path):
    with closing(sqlite3.connect(path)) as connection:
        return tuple(connection.execute("SELECT * FROM " + name).fetchall()
                     for name in ("account", "holding", "trade", "price_quote"))


def test_real_registered_session_can_preview_buy_and_refresh(setup):
    app, database = setup
    client = app.test_client()
    token = register(client)
    headers = {"X-CSRF-Token": token}
    assert b'href="/trade"' in client.get("/market").data
    before = financial_rows(database)
    preview = client.post("/api/orders/preview", json={
        "side": "buy", "symbol": "HPG", "quantity": 1000,
    }, headers=headers)
    assert preview.status_code == 200 and preview.json["estimate_vnd"] == 28_000_000
    assert financial_rows(database) == before
    result = client.post("/api/orders/buy", json={
        "symbol": "HPG", "quantity": 1000,
        "expected_quote_at": preview.json["quote"]["quoted_at"],
    }, headers=headers)
    assert result.status_code == 201 and result.json["cash_vnd"] == 72_000_000
    assert result.json["holding"]["quantity"] == 1000
    init_database(database)  # Both migrations can rerun without resetting finances.
    assert financial_rows(database)[0][0][5] == 72_000_000
    second = app.test_client()
    other_token = register(second, "other@example.test")
    other = second.post("/api/orders/preview", json={
        "side": "buy", "symbol": "HPG", "quantity": 1,
    }, headers={"X-CSRF-Token": other_token})
    assert other.json["cash_vnd"] == 100_000_000 and other.json["available_quantity"] == 0
    old_preview = preview.json["quote"]["quoted_at"]
    refreshed = client.post("/api/simulation/quotes/refresh", json={}, headers=headers)
    assert refreshed.status_code == 200
    rejected = client.post("/api/orders/buy", json={
        "symbol": "HPG", "quantity": 1, "expected_quote_at": old_preview,
    }, headers=headers)
    assert rejected.status_code == 409 and rejected.json["error"]["code"] == "QUOTE_CHANGED"
    assert len(financial_rows(database)[2]) == 1


@pytest.mark.parametrize("scenario,code,status", [
    ("guest", "AUTH_REQUIRED", 401),
    ("csrf", "CSRF_FAILED", 403),
    ("origin", "CSRF_FAILED", 403),
    ("disabled", "ACCOUNT_DISABLED", 403),
    ("expired", "AUTH_REQUIRED", 401),
    ("idle", "AUTH_REQUIRED", 401),
    ("revoked", "AUTH_REQUIRED", 401),
])
def test_auth_rejections_are_safe_json_without_financial_writes(setup, scenario, code, status):
    app, database = setup
    client = app.test_client()
    token = register(client)
    headers = {"X-CSRF-Token": token}
    if scenario == "guest":
        client = app.test_client()
    elif scenario == "csrf":
        headers = {}
    elif scenario == "origin":
        headers["Origin"] = "https://untrusted.example"
    else:
        changes = {
            "disabled": "UPDATE account SET status='disabled'",
            "expired": "UPDATE auth_session SET expires_at='2000-01-01T00:00:00Z'",
            "idle": "UPDATE auth_session SET last_seen_at='2000-01-01T00:00:00Z'",
            "revoked": "UPDATE auth_session SET revoked_at='2000-01-01T00:00:00Z'",
        }
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute(changes[scenario])
    before = financial_rows(database)
    for path in ("/api/orders/buy", "/api/orders/preview", "/api/simulation/quotes/refresh"):
        response = client.post(path, json={}, headers=headers)
        assert response.status_code == status
        assert response.json["error"]["code"] == code
        assert response.headers["Cache-Control"] == "no-store"
    assert financial_rows(database) == before


def test_guest_trade_page_offers_login_without_calling_private_token(setup):
    app, _ = setup
    page = app.test_client().get("/trade")
    assert page.status_code == 200
    assert b'Sign in before trading' in page.data and b'href="/login"' in page.data
    assert b'href="/portfolio"' not in page.data


def test_missing_auth_adapter_still_fails_closed(setup):
    app, _ = setup
    app.extensions.pop("orders_identity")
    response = app.test_client().post("/api/orders/buy", json={})
    assert response.status_code == 503 and response.json["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_portfolio_navigation_is_available_only_with_registered_route(setup):
    app, _ = setup
    # Route contract fixture, not a portfolio implementation or acceptance claim.
    app.add_url_rule("/portfolio", "portfolio.index", lambda: "route fixture")
    client = app.test_client()
    register(client)
    assert b'href="/portfolio"' in client.get("/trade").data
    assert b'href="/portfolio"' in client.get("/market").data
