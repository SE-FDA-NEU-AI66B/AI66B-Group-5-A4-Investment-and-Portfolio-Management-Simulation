"""Actual browser QA with explicit test-only auth, never an M3 acceptance login."""

import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from virtutrade.app import create_app
from virtutrade.orders.errors import OrderError
from virtutrade.simulation.repository import init_demo

with tempfile.TemporaryDirectory(prefix="buy-ui-") as tmp:
    database = Path(tmp) / "demo.db"
    init_demo(database)
    now = datetime.now(timezone.utc)
    with closing(sqlite3.connect(database)) as c, c:
        c.execute(
            "INSERT INTO account(id,email,password_hash,created_at) VALUES(1,'ui@example.test','test-only',?)",
            (now.isoformat(),),
        )
        c.execute(
            "CREATE TABLE auth_session(id INTEGER PRIMARY KEY,account_id INTEGER,expires_at TEXT,revoked_at TEXT)"
        )
        c.execute(
            "INSERT INTO auth_session VALUES(1,1,?,NULL)",
            ((now + timedelta(hours=1)).isoformat(),),
        )
    app = create_app(
        {"TESTING": True, "DATABASE": str(database), "QUOTE_MODE": "simulation"}
    )
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                headless=True,
            )
            page = browser.new_page(viewport={"width": 1200, "height": 850})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            base = f"http://127.0.0.1:{server.server_port}"
            page.goto(base + "/trade")
            expect(page.get_by_role("button", name="Preview order")).to_be_disabled()

            def test_identity(request):
                if request.headers.get("X-CSRF-Token") != "local-test-token":
                    raise OrderError("CSRF_FAILED", "Reload the form and try again.")
                return 1

            app.extensions["orders_identity"] = test_identity
            app.extensions["orders_csrf_token"] = lambda: "local-test-token"
            page.goto(base + "/market")
            page.get_by_role("link", name="Buy shares").click()
            page.get_by_label("Stock symbol").fill("HPG")
            page.get_by_label("Number of shares").fill("4000")
            expect(page.locator("#order-error")).to_contain_text(
                "Exceeds available balance by 12,000,000 VND"
            )
            expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
            page.get_by_label("Number of shares").fill("1000")
            expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
            page.get_by_role("button", name="Confirm buy").click()
            expect(page.locator("#result")).to_contain_text("72,000,000 VND")
            page.get_by_role("button", name="Generate demo quotes").click()
            expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
            page.route("**/api/orders/buy", lambda route: route.abort())
            page.get_by_role("button", name="Confirm buy").click()
            expect(page.locator("#order-error")).to_contain_text(
                "Order result is unknown"
            )
            expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
            expect(page.get_by_role("button", name="Preview order")).to_be_disabled()
            assert not errors, errors
            browser.close()
        with closing(sqlite3.connect(database)) as c:
            assert c.execute("SELECT COUNT(*) FROM trade").fetchone()[0] == 1
            assert c.execute("SELECT cash_vnd FROM account").fetchone()[0] == 72000000
        print(
            "PASS: real browser navigation, missing-auth guard, live shortfall/correction, persisted buy, demo refresh and no automatic retry after ambiguous failure; test auth only."
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
