"""Browser QA using real registration/login and SQLite, with no auth overrides."""
import secrets
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from virtutrade.app import create_app
from virtutrade.simulation.repository import init_demo


def main(loss_mode="disconnect"):
    with tempfile.TemporaryDirectory(prefix="buy-ui-") as tmp:
        database = Path(tmp) / "demo.db"
        init_demo(database)
        app = create_app({"TESTING": True, "DATABASE": str(database),
                          "QUOTE_MODE": "simulation"})
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        email = "ui@example.test"
        password = secrets.token_urlsafe(16)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page(viewport={"width": 1200, "height": 850})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.get_by_role("link", name="Buy shares", exact=True).click()
                expect(page.get_by_role("button", name="Preview order")).to_be_disabled()
                page.get_by_role("link", name="Register", exact=True).click()
                page.get_by_label("Email", exact=True).fill(email)
                page.get_by_label("Password", exact=False).fill(password)
                page.get_by_role("button", name="Register", exact=True).click()
                expect(page.get_by_role("button", name="Log out")).to_be_visible()
                page.get_by_role("link", name="Buy shares", exact=True).click()
                page.get_by_label("Stock symbol").fill("HPG")
                page.get_by_label("Number of shares").fill("4000")
                expect(page.locator("#order-error")).to_contain_text(
                    "Exceeds available balance by 12,000,000 VND")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
                page.get_by_label("Number of shares").fill("1000")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
                page.get_by_role("button", name="Confirm buy").click()
                expect(page.locator("#result")).to_contain_text("72,000,000 VND")
                expect(page.locator("#result")).to_contain_text("Holding: 1000 shares")
                page.get_by_role("link", name="Market", exact=True).click()
                page.get_by_role("button", name="Log out").click()
                page.get_by_role("link", name="Log in", exact=True).click()
                page.get_by_label("Email", exact=True).fill(email)
                page.get_by_label("Password", exact=True).fill(password)
                page.get_by_role("button", name="Log in", exact=True).click()
                page.get_by_role("link", name="Buy shares", exact=True).click()
                page.get_by_label("Stock symbol").fill("HPG")
                page.get_by_label("Number of shares").fill("1")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
                expect(page.locator("#estimate")).to_contain_text("72,000,000 VND")
                page.get_by_role("button", name="Generate demo quotes").click()
                expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
                # Drop the response AFTER a real server commit: no duplicate retry.
                def lose_response(route):
                    response = route.fetch()
                    assert response.status == 201
                    if loss_mode == "gateway":
                        route.fulfill(status=502, content_type="application/json",
                                      body='{"error":{"message":"Gateway unavailable"}}')
                    else:
                        route.abort()
                page.route("**/api/orders/buy", lose_response)
                page.get_by_role("button", name="Confirm buy").click()
                expect(page.locator("#order-error")).to_contain_text("Order result is unknown")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
                expect(page.get_by_role("button", name="Preview order")).to_be_disabled()
                assert not errors, errors
                browser.close()
            with closing(sqlite3.connect(database)) as connection:
                assert connection.execute("SELECT COUNT(*) FROM trade").fetchone()[0] == 2
                assert connection.execute("SELECT cash_vnd FROM account").fetchone()[0] == 71_972_000
                assert connection.execute("SELECT quantity FROM holding").fetchone()[0] == 1001
            print(f"PASS ({loss_mode}): real registration/login/logout, guest guard, shortage/correction, "
                  "persisted buy, demo refresh and ambiguous committed-order handling; "
                  "no fake auth, no provider calls, portfolio acceptance still pending #81.")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    for loss_mode in ("disconnect", "gateway"):
        main(loss_mode)
