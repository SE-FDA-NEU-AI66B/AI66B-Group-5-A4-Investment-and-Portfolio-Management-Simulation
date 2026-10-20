"""Author browser QA for the #101 stock picker and responsive Market-to-Buy UI."""
import argparse
import json
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from virtutrade.app import create_app
from virtutrade.simulation.repository import init_demo


def main(evidence_dir):
    observations = []

    def capture(page, name):
        if evidence_dir:
            evidence_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(evidence_dir / f"{name}.png"), full_page=True)
            observations.append({"state": name, "at_utc": datetime.now(timezone.utc).isoformat()})

    with tempfile.TemporaryDirectory(prefix="market-buy-ui-") as temporary:
        database = Path(temporary) / "simulation.db"
        init_demo(database)
        app = create_app({"TESTING": True, "DATABASE": str(database), "QUOTE_MODE": "simulation"})
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                expect(page.get_by_role("link", name="Buy HPG", exact=True)).to_be_visible()
                expect(page.locator("#breadth-board .breadth-cell")).to_have_count(4)
                expect(page.locator("#ticker-strip .ticker-tile")).to_have_count(6)
                expect(page.locator("#movement-rows tr")).to_have_count(5)
                capture(page, "market-desktop")
                page.get_by_role("link", name="Buy HPG", exact=True).focus()
                # Verify the per-row action and keyboard focus survive polling.
                expect(page.locator("#refresh-status")).to_contain_text("Snapshot refreshed", timeout=10000)
                expect(page.get_by_role("link", name="Buy HPG", exact=True)).to_be_focused()
                # Missing DNSE references must not become flat/zero-change movers.
                snapshot = page.request.get(f"http://127.0.0.1:{server.server_port}/api/market/quotes").json()
                for quote in snapshot["quotes"][:2]:
                    quote.update(source="dnse", change=None, previous_close_vnd=None)

                def missing_reference(route):
                    route.fulfill(json=snapshot)

                page.route("**/api/market/quotes", missing_reference)
                expect(page.locator(".breadth-cell.unclassified strong")).to_have_text("2", timeout=10000)
                expect(page.locator("#movement-rows")).not_to_contain_text("ACB")
                expect(page.locator("#movement-rows")).not_to_contain_text("BID")
                page.unroute("**/api/market/quotes", missing_reference)
                page.get_by_role("link", name="Buy HPG", exact=True).click()
                expect(page.get_by_label("Stock symbol")).to_have_value("HPG")
                expect(page.locator("#selected-name")).to_contain_text("Hoa Phat")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
                page.get_by_role("link", name="Register", exact=True).click()
                page.get_by_label("Email", exact=True).fill("ui-review@example.test")
                disposable = secrets.token_urlsafe(16)
                page.get_by_label("Password", exact=False).fill(disposable)
                page.get_by_role("button", name="Register", exact=True).click()
                page.get_by_role("link", name="Buy HPG", exact=True).click()
                picker = page.get_by_role("combobox", name="Stock symbol")
                expect(picker).to_have_attribute("aria-busy", "false")
                picker.fill("Hoa")
                expect(page.get_by_role("option")).to_have_count(1)
                capture(page, "stock-picker-desktop")
                picker.press("ArrowDown")
                expect(picker).to_have_attribute("aria-activedescendant", "stock-option-0")
                picker.press("Enter")
                expect(picker).to_have_value("HPG")
                expect(picker).to_have_attribute("aria-expanded", "false")
                page.get_by_label("Number of shares").fill("1000")
                page.get_by_role("button", name="Preview order", exact=True).click()
                expect(page.locator("#estimate")).to_contain_text("28,000,000 VND")
                expect(page.locator("#estimate")).to_contain_text("72,000,000 VND")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
                capture(page, "buy-preview-desktop")
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                capture(page, "buy-preview-mobile")
                page.get_by_label("Number of shares").fill("4000")
                expect(page.locator("#order-error")).to_contain_text("12,000,000 VND")
                expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
                capture(page, "buy-shortfall-mobile")
                picker.fill("no-such-company")
                expect(page.locator("#stock-picker-status")).to_contain_text("No matching stocks")
                picker.press("Escape")
                expect(picker).to_have_attribute("aria-expanded", "false")

                # Read-response fixtures only: preserve the real session/database.
                def unavailable(route):
                    route.fulfill(status=503, json={"error": {"code": "MARKET_UNAVAILABLE"}})

                page.route("**/api/market/quotes", unavailable)
                page.get_by_role("link", name="Buy shares", exact=True).click()
                expect(page.locator("#stock-picker-status")).to_contain_text("Could not load stocks")
                capture(page, "picker-error-mobile")
                page.unroute("**/api/market/quotes", unavailable)
                page.get_by_role("button", name="Retry stock list").click()
                expect(page.locator("#stock-picker-status")).to_contain_text("12 stocks available")

                def empty(route):
                    route.fulfill(json={"quotes": []})

                page.route("**/api/market/quotes", empty)
                page.get_by_role("link", name="Buy shares", exact=True).click()
                expect(page.locator("#stock-picker-status")).to_contain_text("No stocks available")
                capture(page, "picker-empty-mobile")
                page.unroute("**/api/market/quotes", empty)
                pending = []
                page.route("**/api/market/quotes", lambda route: pending.append(route))
                page.get_by_role("button", name="Retry stock list").click()
                expect(page.locator("#stock-picker-status")).to_contain_text("Loading available stocks")
                capture(page, "picker-loading-mobile")
                # Complete the held GET with actual server data and check recovery.
                page.wait_for_function("document.getElementById('symbol').getAttribute('aria-busy') === 'true'")
                assert pending
                pending[0].continue_()
                page.unroute("**/api/market/quotes")
                expect(page.locator("#stock-picker-status")).to_contain_text("12 stocks available")
                page.get_by_role("link", name="Market", exact=True).click()
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                table = page.get_by_role("region", name="Stock quotes; scroll horizontally on small screens")
                table.evaluate("element => element.scrollLeft = element.scrollWidth")
                capture(page, "market-mobile")
                expect(page.get_by_role("link", name="Buy HPG", exact=True)).to_be_visible()
                assert not errors, errors
                browser.close()
            if evidence_dir:
                (evidence_dir / "observations.json").write_text(json.dumps({
                    "passed": True, "observations": observations,
                    "limitations": ["Author QA; not independent review or machine verification.",
                                    "GET failures/empty/loading are explicit browser test fixtures.",
                                    "Simulation quotes, not DNSE acceptance.",
                                    "Page captures exclude browser address bar."]
                }, indent=2) + "\n", encoding="utf-8")
            print("PASS: row-to-buy navigation, company search, keyboard selection, preview, shortage, "
                  "read failure/retry, empty/loading states and mobile overflow checks.")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path)
    main(parser.parse_args().evidence_dir)
