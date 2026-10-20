"""Browser QA for sell: real registration, buy, partial/full sale and oversell.

Runs against a disposable simulation database with real auth and SQLite; it
never installs a test identity or calls a market-data provider. Screenshots are
written to docs/images/ui/ as acceptance evidence for #79.
"""

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

EVIDENCE = Path(__file__).resolve().parents[1] / "docs" / "images" / "ui"


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sell-ui-") as tmp:
        database = Path(tmp) / "demo.db"
        init_demo(database)
        app = create_app({"TESTING": True, "DATABASE": str(database),
                          "QUOTE_MODE": "simulation"})
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        email = "sell-ui@example.test"
        password = secrets.token_urlsafe(16)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page(viewport={"width": 1200, "height": 900})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"{base}/register")
                page.get_by_label("Email", exact=True).fill(email)
                page.get_by_label("Password", exact=False).fill(password)
                page.get_by_role("button", name="Register", exact=True).click()
                expect(page.get_by_role("button", name="Log out")).to_be_visible()

                page.get_by_role("link", name="Buy shares", exact=True).click()
                page.get_by_label("Stock symbol").fill("HPG")
                page.get_by_label("Number of shares").fill("1000")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
                page.get_by_role("button", name="Confirm buy").click()
                expect(page.locator("#result")).to_contain_text("Holding: 1000 shares")

                page.get_by_role("link", name="Market", exact=True).click()
                page.get_by_role("link", name="Sell shares", exact=True).click()
                expect(page.get_by_role("link", name="Sell shares", exact=True)).to_have_attribute(
                    "aria-current", "page")
                expect(page.get_by_role("link", name="Buy shares", exact=True)).not_to_have_attribute(
                    "aria-current", "page")
                expect(page.get_by_role("heading", name="Sell shares")).to_be_visible()
                page.get_by_label("Stock symbol").fill("HPG")
                page.get_by_label("Number of shares").fill("400")
                expect(page.locator(".preview-line").filter(
                    has=page.locator("dt", has_text="Shares held")
                ).locator("dd")).to_have_text("1,000")
                expect(page.get_by_role("button", name="Confirm sell")).to_be_enabled()
                page.get_by_role("button", name="Confirm sell").click()
                expect(page.locator("#result")).to_contain_text("Sold 400 HPG")
                expect(page.locator("#result")).to_contain_text("Remaining holding: 600 shares")

                page.get_by_label("Number of shares").fill("800")
                expect(page.locator("#order-error")).to_contain_text(
                    "You hold 600 HPG; the maximum you can sell is 600.")
                expect(page.get_by_role("button", name="Confirm sell")).to_be_disabled()
                page.screenshot(path=str(EVIDENCE / "sell-oversell-warning.png"))

                page.get_by_label("Number of shares").fill("600")
                expect(page.get_by_role("button", name="Confirm sell")).to_be_enabled()
                page.get_by_role("button", name="Confirm sell").click()
                expect(page.locator("#result")).to_contain_text("Sold 600 HPG")
                expect(page.locator("#result")).to_contain_text("Holding fully sold.")
                page.screenshot(path=str(EVIDENCE / "sell-full-sale-result.png"))

                assert not errors, errors
                browser.close()

            with closing(sqlite3.connect(database)) as connection:
                trades = dict(connection.execute(
                    "SELECT side, COUNT(*) FROM trade GROUP BY side").fetchall())
                assert trades == {"buy": 1, "sell": 2}, trades
                assert connection.execute(
                    "SELECT COUNT(*) FROM holding WHERE quantity > 0").fetchone()[0] == 0
                assert connection.execute(
                    "SELECT cash_vnd FROM account").fetchone()[0] > 0
            print("PASS: real registration, buy, partial sale, oversell warning and full "
                  "sale; two screenshots written to docs/images/ui/.")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
