"""Browser QA using real registration/login and SQLite, with no auth overrides."""
import argparse
import json
import secrets
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from virtutrade.app import create_app
from virtutrade.simulation.repository import init_demo


def main(loss_mode="disconnect", evidence_dir=None):
    observations = []

    def capture(page, name):
        if evidence_dir is None:
            return
        evidence_dir.mkdir(parents=True, exist_ok=True)
        filename = f"buy-{loss_mode}-{name}.png"
        page.screenshot(path=str(evidence_dir / filename), full_page=True)
        observations.append({"state": name, "screenshot": filename,
                             "observed_at_utc": datetime.now(timezone.utc).isoformat(),
                             "route": page.url.split(str(server.server_port), 1)[-1]})

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
                capture(page, "guest-guard")
                page.get_by_role("link", name="Register", exact=True).click()
                page.get_by_label("Email", exact=True).fill(email)
                page.get_by_label("Password", exact=False).fill(password)
                page.get_by_role("button", name="Register", exact=True).click()
                expect(page.get_by_role("button", name="Log out")).to_be_visible()
                page.get_by_role("link", name="Buy shares", exact=True).click()
                expect(page.locator("#preview-placeholder")).to_be_visible()
                expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
                capture(page, "empty")
                page.route("**/api/market/quotes", lambda route: route.fulfill(
                    status=503, content_type="application/json", body='{"error":"read failed"}'))
                page.reload()
                expect(page.locator("#stock-picker-status")).to_contain_text("Could not load stocks")
                symbol = page.get_by_label("Stock symbol")
                symbol.fill("HPG")
                expect(page.get_by_role("button", name="Retry stock list")).to_be_visible()
                capture(page, "picker-read-failure")
                page.unroute("**/api/market/quotes")
                page.get_by_role("button", name="Retry stock list").click()
                expect(page.locator("#stock-picker-status")).to_contain_text("stocks available")
                assert symbol.input_value() == "HPG"
                symbol.focus()
                symbol.press("ArrowDown")
                symbol.press("Enter")
                assert symbol.input_value() == "HPG"
                assert symbol.evaluate("input => document.activeElement === input")
                quantity = page.get_by_label("Number of shares")
                for invalid_quantity in ("0", "-1", "1.5"):
                    quantity.fill(invalid_quantity)
                    page.get_by_role("button", name="Preview order").click()
                    message = "Quantity must be a whole number of at least 1 share."
                    expect(page.locator("#order-error")).to_have_text(message)
                    assert quantity.evaluate("(input) => input.validationMessage") == message
                    expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
                    expect(page.locator("#estimate")).to_be_hidden()
                    if invalid_quantity == "0":
                        capture(page, "zero-quantity")
                page.route("**/api/orders/preview", lambda route: route.fulfill(
                    status=503, content_type="application/json",
                    body='{"error":{"code":"QUOTE_UNAVAILABLE","message":"No valid price is available. Return to Market and try again later."}}'))
                quantity.fill("1")
                expect(page.locator("#order-error")).to_contain_text("generate demo quotes")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
                assert symbol.input_value() == "HPG" and quantity.input_value() == "1"
                capture(page, "quote-unavailable")
                page.unroute("**/api/orders/preview")
                page.get_by_role("button", name="Preview order").click()
                expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
                page.route("**/api/orders/preview", lambda route: route.abort())
                page.get_by_role("button", name="Preview order").click()
                expect(page.locator("#order-error")).to_contain_text("stock and quantity are saved")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
                assert symbol.input_value() == "HPG" and quantity.input_value() == "1"
                capture(page, "preview-read-failure")
                page.unroute("**/api/orders/preview")
                page.get_by_role("button", name="Preview order").click()
                expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
                page.evaluate("""() => {
                    const original = window.fetch;
                    window.__releasePreview = null;
                    window.fetch = (url, options) => url === '/api/orders/preview'
                        ? new Promise(resolve => {
                            window.__releasePreview = () => resolve(original(url, options));
                          })
                        : original(url, options);
                    window.__restoreFetch = () => { window.fetch = original; };
                }""")
                page.get_by_label("Number of shares").fill("4000")
                expect(page.locator("#order-status")).to_contain_text("Loading preview")
                capture(page, "loading")
                page.evaluate("window.__releasePreview()")
                page.evaluate("window.__restoreFetch()")
                assert quantity.evaluate("(input) => input.validationMessage") == ""
                expect(page.locator("#order-error")).to_contain_text(
                    "Exceeds available balance by 12,000,000 VND")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
                expect(page.locator("#order-status")).to_have_text("Adjust the quantity to continue.")
                capture(page, "shortfall")
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                capture(page, "shortfall-mobile")
                page.set_viewport_size({"width": 1200, "height": 850})
                page.get_by_label("Number of shares").fill("1000")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
                capture(page, "corrected-preview")
                with closing(sqlite3.connect(database)) as connection, connection:
                    connection.execute(
                        "UPDATE price_quote SET quoted_at=? WHERE instrument_id="
                        "(SELECT id FROM instrument WHERE symbol='HPG')",
                        (datetime.now(timezone.utc).isoformat(),),
                    )
                page.get_by_role("button", name="Confirm buy").click()
                expect(page.locator("#order-error")).to_contain_text("Price changed")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
                capture(page, "quote-changed")
                with closing(sqlite3.connect(database)) as connection:
                    assert connection.execute("SELECT COUNT(*) FROM trade").fetchone()[0] == 0
                page.get_by_role("button", name="Preview order").click()
                expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
                page.get_by_role("button", name="Confirm buy").click()
                expect(page.locator("#result")).to_contain_text("72,000,000 VND")
                expect(page.locator("#result")).to_contain_text("Holding: 1000 shares")
                expect(page.locator("#estimate")).to_be_hidden()
                capture(page, "receipt")
                # Test fixture: age the stored quote so the UI exercises a real
                # server rejection; recovery must use the visible demo control.
                with closing(sqlite3.connect(database)) as connection, connection:
                    connection.execute(
                        "UPDATE price_quote SET quoted_at = ?",
                        ((datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat(),),
                    )
                page.get_by_role("button", name="Preview order").click()
                expect(page.locator("#order-error")).to_contain_text(
                    "Price may be delayed. Generate demo quotes, then preview again.")
                expect(page.locator("#order-status")).to_have_text(
                    "Preview unavailable. Review the message below.")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
                capture(page, "stale-quote")
                page.get_by_role("button", name="Generate demo quotes").click()
                expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
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
                capture(page, "unknown-result")
                assert not errors, errors
                browser.close()
            with closing(sqlite3.connect(database)) as connection:
                assert connection.execute("SELECT COUNT(*) FROM trade").fetchone()[0] == 2
                assert connection.execute("SELECT cash_vnd FROM account").fetchone()[0] == 71_972_000
                assert connection.execute("SELECT quantity FROM holding").fetchone()[0] == 1001
            if evidence_dir is not None:
                report = {"scenario": loss_mode, "passed": True, "observations": observations,
                          "database_assertions": {"trades": 2, "cash_vnd": 71_972_000, "shares": 1001},
                          "limitations": ["Author QA, not independent-machine acceptance.",
                                          "Page captures exclude browser chrome/address bar.",
                                          "Picker/read failures and QUOTE_UNAVAILABLE use intercepted failures; no provider call is claimed.",
                                          "Stale and changed quotes use a controlled temporary-database fixture.",
                                          "Portfolio valuation is outside #116; the link is visible."]}
                (evidence_dir / f"buy-{loss_mode}.json").write_text(
                    json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(f"PASS ({loss_mode}): real registration/login/logout, guest guard, "
                  "empty/loading/error/success states, keyboard picker, mobile layout, "
                  "shortage/correction, persisted buy, quote recovery and ambiguous "
                  "committed-order handling; no fake auth or provider calls.")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, help="Save page captures and sanitized QA results")
    args = parser.parse_args()
    for loss_mode in ("disconnect", "gateway"):
        main(loss_mode, args.evidence_dir)
