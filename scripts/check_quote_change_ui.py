"""#106 browser evidence with real auth/SQLite; only the quote is a fixture."""

import argparse
import secrets
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from virtutrade.app import create_app
from virtutrade.simulation.repository import init_demo


def money_state(database):
    with closing(sqlite3.connect(database)) as connection:
        return tuple(connection.execute("SELECT * FROM " + table).fetchall()
                     for table in ("account", "holding", "trade"))


def main(evidence_dir=None):
    if evidence_dir:
        evidence_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="quote-change-ui-") as temporary:
        database = Path(temporary) / "simulation.db"
        init_demo(database)
        app = create_app({"TESTING": True, "DATABASE": str(database),
                          "QUOTE_MODE": "simulation"})
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page(viewport={"width": 1200, "height": 900})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                base = f"http://127.0.0.1:{server.server_port}"
                page.goto(base + "/register")
                page.get_by_label("Email", exact=True).fill("quote-check@example.test")
                page.get_by_label("Password", exact=False).fill(secrets.token_urlsafe(16))
                page.get_by_role("button", name="Register", exact=True).click()
                page.get_by_role("link", name="Buy shares", exact=True).click()
                page.get_by_label("Stock symbol").fill("HPG")
                page.get_by_label("Number of shares").fill("1000")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
                page.get_by_role("button", name="Confirm buy").click()
                expect(page.locator("#result")).to_contain_text("Holding: 1000 shares")

                # This check targets quote acceptance, not Portfolio navigation.
                page.goto(base + "/trade?side=sell&symbol=HPG")
                page.get_by_label("Number of shares").fill("1000")
                expect(page.get_by_role("button", name="Confirm sell")).to_be_enabled()
                before = money_state(database)
                with closing(sqlite3.connect(database)) as connection, connection:
                    connection.execute(
                        "UPDATE price_quote SET price_vnd=27500, quoted_at=? "
                        "WHERE instrument_id=(SELECT id FROM instrument WHERE symbol='HPG')",
                        (datetime.now(timezone.utc).isoformat(),),
                    )
                with page.expect_response(lambda response: response.url.endswith("/api/orders/sell")) as rejected:
                    page.get_by_role("button", name="Confirm sell").click()
                assert rejected.value.status == 409
                assert rejected.value.json()["error"]["code"] == "QUOTE_CHANGED"
                expect(page.locator("#order-error")).to_have_text(
                    "Price changed; refresh the preview before confirming.")
                expect(page.locator("#order-status")).to_have_text(
                    "Order was not placed. Review the message, then preview again.")
                expect(page.locator("#estimate")).to_be_hidden()
                expect(page.get_by_role("button", name="Confirm sell")).to_be_disabled()
                assert money_state(database) == before
                if evidence_dir:
                    page.screenshot(path=str(evidence_dir / "sell-quote-changed.png"),
                                    full_page=True)

                page.get_by_role("button", name="Preview order").click()
                expect(page.locator("#estimate")).to_contain_text("27,500,000 VND")
                expect(page.get_by_role("button", name="Confirm sell")).to_be_enabled()
                page.get_by_role("button", name="Confirm sell").click()
                expect(page.locator("#result")).to_contain_text("Sold 1000 HPG")
                expect(page.locator("#result")).to_contain_text("99,500,000 VND")
                if evidence_dir:
                    page.screenshot(path=str(evidence_dir / "sell-repreview-filled.png"),
                                    full_page=True)
                with closing(sqlite3.connect(database)) as connection, connection:
                    assert connection.execute(
                        "SELECT fill_price_vnd, quantity FROM trade WHERE side='sell'"
                    ).fetchall() == [(27500, 1000)]
                    connection.execute("UPDATE price_quote SET price_vnd=29000")
                    assert connection.execute(
                        "SELECT fill_price_vnd FROM trade WHERE side='sell'"
                    ).fetchall() == [(27500,)]
                    assert connection.execute("SELECT COUNT(*) FROM holding").fetchone()[0] == 0
                assert not errors, errors
                browser.close()
            print("PASS: changed quote rejects without money writes; explicit re-preview "
                  "fills at 27,500 VND; later tick leaves the recorded fill unchanged.")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path)
    main(parser.parse_args().evidence_dir)
