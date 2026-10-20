"""P0 acceptance audit (#82): every P0 journey and business-rule error in a browser.

Starts the real app on a disposable simulation database. Accounts are created through
the real registration form; there are no auth overrides and no market-data
provider calls. Every check records what the page actually showed. A failed check is
recorded and the audit moves on, so the matrix shows what works and what does not.

Database writes made by this script are test fixtures, and each one is labelled:
- ageing a quote (stale price),
- setting one price (sell at a gain),
- emptying the quote table (empty state).

Usage (after SETUP, with the optional QA dependency `playwright==1.63.0`):

    python scripts/check_p0_journeys.py --evidence-dir docs/images/ui/p0-audit

`--browser` takes msedge (default), chrome or chromium. Exit code 1 means at
least one check failed; read p0-results.md in the evidence directory.
"""

import argparse
import json
import platform
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from virtutrade.app import create_app
from virtutrade.database import init_database
from virtutrade.simulation.repository import init_demo

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT_MS = 4000


class Audit:
    def __init__(self, evidence_dir):
        self.evidence_dir = evidence_dir
        self.results = []

    def check(self, check_id, story, title, expected, action, page=None, shot=None):
        """Run one check. `action` returns the observed text or raises AssertionError."""
        started = time.perf_counter()
        try:
            observed, passed = action(), True
        except AssertionError as exc:
            observed, passed = _first_line(exc), False
        screenshot = None
        if page is not None and shot and self.evidence_dir is not None:
            self.evidence_dir.mkdir(parents=True, exist_ok=True)
            screenshot = f"{check_id}-{shot}.png"
            page.screenshot(path=str(self.evidence_dir / screenshot), full_page=True)
        self.results.append({
            "id": check_id, "story": story, "check": title, "expected": expected,
            "observed": observed, "result": "PASS" if passed else "FAIL",
            "screenshot": screenshot, "seconds": round(time.perf_counter() - started, 2),
        })
        print(f"{'PASS' if passed else 'FAIL'} {check_id} {title}: {observed}")


    def snap(self, page, name):
        """Extra capture inside a check, e.g. a second page or an intermediate state."""
        if self.evidence_dir is not None:
            self.evidence_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(self.evidence_dir / f"{name}.png"), full_page=True)


def _first_line(exc):
    text = str(exc).strip().splitlines()
    return text[0][:300] if text else type(exc).__name__


def _serve(app):
    server = make_server("127.0.0.1", 0, app, threaded=True)
    Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}"


def _sql(database, statement, params=()):
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(statement, params)


def _scalar(database, query, params=()):
    with closing(sqlite3.connect(database)) as connection:
        return connection.execute(query, params).fetchone()[0]


def _commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _register(page, base, email, password):
    page.goto(f"{base}/register")
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=False).fill(password)
    page.get_by_role("button", name="Register", exact=True).click()
    expect(page.get_by_role("button", name="Log out")).to_be_visible()


def _login(page, base, email, password):
    page.goto(f"{base}/login")
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=False).fill(password)
    page.get_by_role("button", name="Log in", exact=True).click()


def _logout(page, base):
    page.goto(f"{base}/market")
    page.get_by_role("button", name="Log out").click()


def _fill_order(page, symbol, quantity):
    page.get_by_label("Stock symbol").fill(symbol)
    page.get_by_label("Number of shares").fill(str(quantity))
    page.get_by_role("button", name="Preview order").click()


def _status(page):
    return page.locator("#order-status").inner_text()


def _error(page):
    return page.locator("#order-error").inner_text()


def run(audit, browser_name, executable_path=None):
    with tempfile.TemporaryDirectory(prefix="p0-audit-") as tmp:
        database = Path(tmp) / "p0.db"
        init_demo(database)
        app = create_app({"TESTING": True, "DATABASE": str(database), "QUOTE_MODE": "simulation"})
        server, base = _serve(app)
        empty_db = Path(tmp) / "empty.db"
        init_database(empty_db)
        _sql(empty_db, "DELETE FROM price_quote")  # Fixture: empty market.
        empty_server, empty_base = _serve(create_app({"TESTING": True, "DATABASE": str(empty_db)}))
        broken_server, broken_base = _serve(create_app(
            {"TESTING": True, "DATABASE": str(Path(tmp) / "missing" / "none.db")}))
        investor = ("investor@example.test", secrets.token_urlsafe(16))
        second = ("second@example.test", secrets.token_urlsafe(16))
        locked = ("locked@example.test", secrets.token_urlsafe(16))
        try:
            with sync_playwright() as playwright:
                launch = {"headless": True}
                if executable_path:
                    launch["executable_path"] = executable_path
                elif browser_name != "chromium":
                    launch["channel"] = browser_name
                browser = playwright.chromium.launch(**launch)
                audit.browser = f"{browser_name} {browser.version}"
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.set_default_timeout(TIMEOUT_MS)
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                _journeys(audit, browser, page, base, database, investor, second, locked)
                _states(audit, browser, empty_base, broken_base)
                _login(page, base, *investor)  # The journey ended logged out.
                _layout_and_keyboard(audit, page, base)

                def no_script_errors():
                    assert not page_errors, f"JavaScript errors: {page_errors}"
                    return "No uncaught JavaScript errors during the audit"
                audit.check("X04", "All", "No uncaught JavaScript errors",
                            "Zero page errors", no_script_errors)
                browser.close()
        finally:
            for running in (server, empty_server, broken_server):
                running.shutdown()
                running.server_close()


def _journeys(audit, browser, page, base, database, investor, second, locked):
    email, password = investor
    check = audit.check

    # US01 / US02: register, errors, grant, login, lockout.
    def landing():
        page.goto(f"{base}/")
        expect(page.get_by_role("link", name="Register", exact=True)).to_be_visible()
        expect(page.get_by_role("link", name="Log in", exact=True)).to_be_visible()
        return f"/ opens {page.url.replace(base, '')} with Log in and Register links"
    check("US01-1", "US01", "Guest landing offers register and sign in",
          "Documented landing / shows Log in and Register", landing, page, "landing")

    def register_error(field_email, field_password, expected_text):
        def action():
            page.goto(f"{base}/register")
            page.get_by_label("Email", exact=True).fill(field_email)
            page.get_by_label("Password", exact=False).fill(field_password)
            # Bypass the browser's own hint so the server-side rule is exercised.
            page.locator("form").evaluate("form => form.noValidate = true")
            page.get_by_role("button", name="Register", exact=True).click()
            expect(page.get_by_role("alert")).to_have_text(expected_text)
            return page.get_by_role("alert").inner_text()
        return action
    check("US01-2", "US01", "Invalid email is rejected", "Enter a valid email address.",
          register_error("not-an-email", password, "Enter a valid email address."), page, "invalid-email")
    check("US01-3", "US01", "Password shorter than 8 is rejected",
          "Password must be 8..128 characters.",
          register_error(email, "short", "Password must be 8..128 characters."), page, "short-password")

    def register_ok():
        _register(page, base, email, password)
        expect(page.locator("header")).to_contain_text(email)
        return f"Account created; landed on {page.url.replace(base, '')} signed in as {email}"
    check("US01-4", "US01", "Valid registration signs the user in",
          "Account created and logged-in home shown", register_ok, page, "registered")

    def grant():
        expect(page.locator("header")).to_contain_text("100,000,000 VND")
        assert _scalar(database, "SELECT cash_vnd FROM account WHERE email = ?", (email,)) == 100_000_000
        return "Header shows 100,000,000 VND; database cash 100,000,000"
    check("US02-1", "US02", "New account receives exactly 100,000,000 VND",
          "Balance shows 100,000,000 VND", grant, page, "grant")

    def duplicate():
        other = browser.new_page()
        other.set_default_timeout(TIMEOUT_MS)
        other.goto(f"{base}/register")
        other.get_by_label("Email", exact=True).fill(email.upper())
        other.get_by_label("Password", exact=False).fill(secrets.token_urlsafe(16))
        other.get_by_role("button", name="Register", exact=True).click()
        expect(other.get_by_role("alert")).to_have_text("Email already in use")
        observed = other.get_by_role("alert").inner_text()
        other.close()
        return f"{observed} (same email in upper case)"
    check("US01-5", "US01", "Duplicate email is rejected", "Email already in use", duplicate)

    def lockout():
        lock_page = browser.new_page()
        lock_page.set_default_timeout(TIMEOUT_MS)
        _register(lock_page, base, *locked)
        _logout(lock_page, base)
        messages = []
        for _ in range(5):
            _login(lock_page, base, locked[0], "wrong-password-123")
            messages.append(lock_page.get_by_role("alert").inner_text())
        _login(lock_page, base, *locked)  # Correct password while locked.
        messages.append(lock_page.get_by_role("alert").inner_text())
        lock_page.close()
        assert messages[3] == "Invalid email or password", messages
        assert "Account locked" in messages[4] and "900 seconds" in messages[4], messages
        assert "Account locked" in messages[5], messages
        return f"Attempts 1-4: '{messages[0]}'; attempt 5 and correct password: '{messages[5]}'"
    check("US01-6", "US01", "Five wrong passwords lock the account for 15 minutes",
          "Locked after the 5th wrong password; 900 s", lockout)

    # US03: market data, freshness, search.
    def market_rows():
        page.goto(f"{base}/market")
        rows = page.locator("#quote-rows tr")
        expect(rows).to_have_count(12)
        first = rows.first.inner_text().replace("\n", " ").replace("\t", " ")
        return f"12 rows with price, change, UTC timestamp and source; first: {first}"
    check("US03-1", "US03", "Market lists price, daily change and last update",
          "Price, % change and timestamp per ticker", market_rows, page, "market")

    def stale_market():
        # Fixture: HPG quote aged 20 minutes in the disposable database.
        aged = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
        _sql(database, "UPDATE price_quote SET quoted_at = ? WHERE instrument_id ="
             " (SELECT id FROM instrument WHERE symbol = 'HPG')", (aged,))
        page.reload()
        row = page.locator("#quote-rows tr", has_text="HPG")
        expect(row).to_contain_text("Price may be delayed")
        return "HPG row shows 'Price may be delayed' (quote aged 20 min by fixture)"
    check("US03-2", "US03", "Quote older than 15 minutes is flagged",
          "Price may be delayed", stale_market, page, "stale")

    def search_detail():
        page.goto(f"{base}/market")
        search = page.get_by_role("searchbox")
        assert search.count() > 0, "No ticker search box or detail page on /market (pending #85)"
        return "Search box present"
    check("US03-3", "US03", "Search a ticker and open its detail page",
          "Search + detail view with price, change, time", search_detail)

    def unknown_ticker():
        page.goto(f"{base}/market")
        search = page.get_by_role("searchbox")
        assert search.count() > 0, ("No market search, so 'Ticker not found' cannot be shown on "
                                    "/market (pending #85); /trade shows it on preview (US04-4)")
        search.fill("ZZZ")
        expect(page.get_by_text("Ticker not found")).to_be_visible()
        return "Ticker not found"
    check("US03-4", "US03", "Unknown ticker search shows 'Ticker not found'",
          "Ticker not found", unknown_ticker)

    # US04 / US10: buy.
    def guest_guard():
        guest = browser.new_page()
        guest.set_default_timeout(TIMEOUT_MS)
        guest.goto(f"{base}/trade")
        expect(guest.get_by_role("button", name="Preview order")).to_be_disabled()
        observed = guest.locator("aside").inner_text()
        response = guest.request.post(f"{base}/api/orders/buy", data={"symbol": "HPG", "quantity": 1})
        assert response.status == 401, response.status
        guest.close()
        return f"Preview disabled; '{observed}'; direct API buy -> 401"
    check("US04-1", "US04", "Guest cannot trade", "Sign-in guidance; API 401", guest_guard)

    def reach_buy():
        page.goto(f"{base}/market")
        page.get_by_role("link", name="Buy shares", exact=True).click()
        aged = _scalar(database, "SELECT quoted_at FROM price_quote JOIN instrument"
                       " ON instrument.id = price_quote.instrument_id WHERE symbol = 'HPG'")
        page.get_by_role("button", name="Generate demo quotes").click()  # Recover the aged quote.
        expect(page.get_by_role("button", name="Generate demo quotes")).to_be_enabled()
        fresh = _scalar(database, "SELECT quoted_at FROM price_quote JOIN instrument"
                        " ON instrument.id = price_quote.instrument_id WHERE symbol = 'HPG'")
        assert fresh > aged, (aged, fresh)
        _sql(database, "UPDATE price_quote SET price_vnd = 28000 WHERE instrument_id ="
             " (SELECT id FROM instrument WHERE symbol = 'HPG')")  # Fixture: AC reference price.
        return f"Market -> Buy shares link -> {page.url.replace(base, '')}; demo quotes regenerated"
    check("US04-2", "US04", "Buy form reachable from Market without typing a URL",
          "Visible link from /market to /trade", reach_buy)

    def preview_no_write():
        _fill_order(page, "HPG", 1000)
        expect(page.locator("#estimate")).to_contain_text("28,000,000 VND")
        assert _scalar(database, "SELECT COUNT(*) FROM trade") == 0
        return "Estimate 28,000,000 VND for 1,000 HPG at 28,000; 0 trades recorded"
    check("US04-3", "US04", "Preview 1,000 HPG costs 28,000,000 and writes nothing",
          "28,000,000 VND; no trade", preview_no_write, page, "buy-preview")

    def unknown_on_trade():
        _fill_order(page, "ZZZ", 10)
        expect(page.locator("#order-error")).to_have_text("Ticker not found. Choose a stock from Market.")
        return _error(page)
    check("US04-4", "US04", "Unknown ticker on the order form",
          "Ticker not found", unknown_on_trade, page, "buy-unknown")

    def zero_quantity():
        _fill_order(page, "HPG", 0)
        expect(page.locator("#order-status")).to_contain_text("whole number")
        hint = page.get_by_label("Number of shares").evaluate("input => input.validationMessage")
        observed = f"{_status(page)} {_error(page)}".strip() + f" (browser hint: '{hint}')"
        expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
        assert "Quantity must be a whole number of at least 1 share" in observed, (
            f"Visible text is '{observed}', not the AC wording "
            "'Quantity must be a whole number of at least 1 share'")
        return observed
    check("US04-5", "US04", "Buy 0 shares is rejected with the AC message",
          "Quantity must be a whole number of at least 1 share", zero_quantity, page, "buy-zero")

    def over_budget():
        _fill_order(page, "HPG", 4000)
        expect(page.locator("#order-error")).to_contain_text("Exceeds available balance by 12,000,000 VND")
        expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
        return f"{_error(page)} Confirm disabled."
    check("US10-1", "US10", "Over-budget order shows the inline warning and disables confirm",
          "Exceeds available balance by 12,000,000 VND; confirm disabled",
          over_budget, page, "us10-warning")

    def corrected():
        page.get_by_label("Number of shares").fill("1000")
        page.get_by_role("button", name="Preview order").click()
        expect(page.locator("#order-error")).to_have_text("")
        expect(page.get_by_role("button", name="Confirm buy")).to_be_enabled()
        return "Warning cleared and Confirm buy re-enabled at 1,000 shares"
    check("US10-2", "US10", "Correcting the quantity clears the warning",
          "Warning disappears; confirm re-enabled", corrected)

    def buy_fill():
        page.get_by_role("button", name="Confirm buy").click()
        expect(page.locator("#result")).to_contain_text("Cash remaining: 72,000,000 VND")
        expect(page.locator("#result")).to_contain_text("Holding: 1000 shares")
        return page.locator("#result").inner_text()
    check("US04-6", "US04", "Buy 1,000 HPG fills at 28,000",
          "Cash 72,000,000 VND; holding 1,000 HPG", buy_fill, page, "buy-receipt")

    def insufficient_cash():
        token = _csrf(page)
        quote = page.request.post(f"{base}/api/orders/preview", headers=token, data={
            "side": "buy", "symbol": "FPT", "quantity": 3000}).json()
        # Bypass the disabled button: the server must enforce BR1 on its own.
        response = page.request.post(f"{base}/api/orders/buy", headers=token, data={
            "symbol": "FPT", "quantity": 3000, "expected_quote_at": quote["quote"]["quoted_at"]})
        message = response.json()["error"]["message"]
        _fill_order(page, "FPT", 3000)
        expect(page.locator("#order-error")).to_contain_text("Exceeds available balance by 288,000,000 VND")
        expect(page.get_by_role("button", name="Confirm buy")).to_be_disabled()
        ui = _error(page)
        assert response.status == 409, response.status
        assert message.startswith("Insufficient cash: this order needs 360,000,000 VND but only "
                                  "72,000,000 VND is available"), message
        return f"Form: '{ui}' (confirm disabled). Server on bypass: 409 '{message}'"
    check("US04-7", "US04", "3,000 FPT with 72,000,000 cash is rejected (BR1)",
          "Insufficient cash: this order needs 360,000,000 VND but only 72,000,000 VND is available",
          insufficient_cash, page, "buy-insufficient")

    # US06 before selling, then US05.
    def portfolio_after_buy():
        page.goto(f"{base}/market")
        page.get_by_role("link", name="Portfolio", exact=True).click()
        row = page.locator("tbody tr", has_text="HPG")
        expect(row).to_contain_text("1,000")
        expect(row).to_contain_text("28,000.00")
        expect(page.locator(".totals")).to_contain_text("100,000,000")
        return "Market -> Portfolio: HPG 1,000 @ 28,000.00; total = cash + holdings = 100,000,000"
    check("US06-1", "US06", "Portfolio shows the bought holding and total value",
          "Quantity, average cost, market value, total = cash + holdings",
          portfolio_after_buy, page, "portfolio")

    def reach_sell():
        # Fixture: HPG rises to 30,000 so the sale realises a gain.
        _sql(database, "UPDATE price_quote SET price_vnd = 30000, quoted_at = ? WHERE instrument_id ="
             " (SELECT id FROM instrument WHERE symbol = 'HPG')",
             (datetime.now(timezone.utc).isoformat(),))
        page.reload()
        expect(page.locator("tbody tr", has_text="HPG")).to_contain_text("+2,000,000")
        audit.snap(page, "US05-1-portfolio-gain")
        page.locator("tbody tr", has_text="HPG").get_by_role("link", name="Sell").click()
        expect(page.get_by_role("heading", name="Sell shares")).to_be_visible()
        return f"Portfolio shows +2,000,000 unrealised; Sell link -> {page.url.replace(base, '')}"
    check("US05-1", "US05", "Sell reachable from the holding row",
          "Visible Sell link; unrealised +2,000,000 at 30,000", reach_sell, page, "sell-form")

    def oversell():
        _fill_order(page, "HPG", 500)
        page.get_by_role("button", name="Confirm sell").click()
        expect(page.locator("#result")).to_contain_text("Remaining holding: 500 shares")
        _fill_order(page, "HPG", 800)
        expect(page.locator("#order-error")).to_contain_text(
            "You hold 500 HPG; the maximum you can sell is 500")
        expect(page.get_by_role("button", name="Confirm sell")).to_be_disabled()
        return f"After selling 500: {_error(page)} Confirm disabled."
    check("US05-2", "US05", "Selling 800 while holding 500 is rejected (BR2)",
          "You hold 500 HPG; the maximum you can sell is 500", oversell, page, "oversell")

    def full_sale():
        cash_before = _scalar(database, "SELECT cash_vnd FROM account WHERE email = ?", (email,))
        _fill_order(page, "HPG", 500)
        page.get_by_role("button", name="Confirm sell").click()
        expect(page.locator("#result")).to_contain_text("Holding fully sold")
        result = page.locator("#result").inner_text()
        cash_after = _scalar(database, "SELECT cash_vnd FROM account WHERE email = ?", (email,))
        assert cash_after - cash_before == 15_000_000, (cash_before, cash_after)
        realised = _scalar(database, "SELECT SUM(realised_pnl_vnd) FROM trade WHERE side = 'sell'")
        assert realised == 2_000_000, realised
        return f"{result} Two sales of 500 at 30,000: total realised +2,000,000; cash +30,000,000"
    check("US05-3", "US05", "Selling all 1,000 HPG at 30,000 realises +2,000,000",
          "Proceeds 30,000,000; realised +2,000,000; holding 0", full_sale, page, "sell-full")

    def quote_changed():
        # Buy one share so a sell preview exists, then change the quote before confirming.
        page.goto(f"{base}/trade")
        _fill_order(page, "HPG", 1)
        page.get_by_role("button", name="Confirm buy").click()
        expect(page.locator("#result")).to_contain_text("Holding: 1 shares")
        page.goto(f"{base}/trade?side=sell&symbol=HPG")
        _fill_order(page, "HPG", 1)
        expect(page.get_by_role("button", name="Confirm sell")).to_be_enabled()
        _sql(database, "UPDATE price_quote SET price_vnd = 27500, quoted_at = ? WHERE instrument_id ="
             " (SELECT id FROM instrument WHERE symbol = 'HPG')",
             (datetime.now(timezone.utc).isoformat(),))  # Fixture: quote moves after preview.
        page.get_by_role("button", name="Confirm sell").click()
        expect(page.locator("#order-error")).not_to_have_text("")
        observed = _error(page)
        assert "Sold" in page.locator("#result").inner_text(), (
            f"Order rejected: '{observed}'. AC expects a fill at the previewed 30,000; the API "
            "contract instead returns 409 QUOTE_CHANGED (documented deviation)")
        return observed
    check("US05-4", "US05", "Quote change after submit still fills at the submitted price",
          "Filled at the previewed price (BR3)", quote_changed, page, "quote-changed")

    def isolation_and_empty():
        other = browser.new_page()
        other.set_default_timeout(TIMEOUT_MS)
        _register(other, base, *second)
        other.get_by_role("link", name="Portfolio", exact=True).click()
        expect(other.get_by_text("No positions yet")).to_be_visible()
        expect(other.locator(".totals")).to_contain_text("100,000,000")
        assert other.locator("tbody tr", has_text="HPG").count() == 0
        audit.snap(other, "US06-2-empty")
        other.close()
        return "Second account: 'No positions yet', total 100,000,000, none of the first account's HPG"
    check("US06-2", "US06", "Empty account shows 'No positions yet'; accounts are isolated",
          "No positions yet; total = cash", isolation_and_empty)

    def login_lands_portfolio():
        _logout(page, base)
        _login(page, base, email, password)
        landed = page.url.replace(base, "")
        assert landed == "/portfolio", (f"Login lands on {landed}; AC says the user reaches their "
                                        "own portfolio. Portfolio is one click away in the header")
        return landed
    check("US01-7", "US01", "Sign-in reaches the user's own portfolio",
          "/portfolio after login", login_lands_portfolio)

    def no_regrant():
        page.goto(f"{base}/portfolio")
        cash = _scalar(database, "SELECT cash_vnd FROM account WHERE email = ?", (email,))
        flows = _scalar(database, "SELECT COALESCE(SUM(CASE side WHEN 'sell' THEN 1 ELSE -1 END"
                        " * quantity * fill_price_vnd), 0) FROM trade JOIN account"
                        " ON account.id = trade.account_id WHERE email = ?", (email,))
        assert cash == 100_000_000 + flows, (cash, flows)
        expect(page.locator(".totals")).to_contain_text(f"{cash:,}")
        return (f"After logout/login cash is {cash:,} VND = 100,000,000 {flows:+,} from trades; "
                "no second grant")
    check("US02-2", "US02", "Balance changes only through trades",
          "No re-grant on login", no_regrant)

    def portfolio_speed():
        started = time.perf_counter()
        page.goto(f"{base}/portfolio")
        expect(page.locator(".totals")).to_be_visible()
        elapsed = time.perf_counter() - started
        assert elapsed < 2, elapsed
        return f"Loaded in {elapsed * 1000:.0f} ms (target 2,000 ms)"
    check("US06-3", "US06", "Portfolio loads within 2 seconds", "< 2 s", portfolio_speed)

    def guest_portfolio():
        guest = browser.new_page()
        guest.set_default_timeout(TIMEOUT_MS)
        response = guest.goto(f"{base}/portfolio")
        assert response.status == 401, response.status
        expect(guest.get_by_role("heading", level=1)).to_have_text("Sign in to see your portfolio.")
        guest.close()
        return "401 page 'Sign in to see your portfolio.' with Log in / Create an account"
    check("US06-4", "US06", "Guest cannot open a portfolio", "401 with sign-in guidance", guest_portfolio)

    def loading():
        page.goto(f"{base}/trade")
        held = []
        page.route("**/api/orders/preview", lambda route: held.append(route))
        page.get_by_label("Stock symbol").fill("HPG")
        page.get_by_label("Number of shares").fill("1")
        page.get_by_role("button", name="Preview order").click()
        expect(page.locator("#order-status")).to_have_text("Loading preview…")
        observed = _status(page)
        held[0].continue_()
        page.unroute("**/api/orders/preview")
        expect(page.locator("#order-status")).to_have_text("Check the quote, then confirm.")
        return f"While the request is held: '{observed}' in an aria-live status; then the preview"
    check("S03", "US04", "Loading state is announced", "Visible aria-live loading status",
          loading, page)

    def revoked_session():
        token = _csrf(page)
        _logout(page, base)
        response = page.request.post(f"{base}/api/orders/preview", headers=token, data={
            "side": "buy", "symbol": "HPG", "quantity": 1})
        assert response.status == 401, response.status
        page.goto(f"{base}/trade")
        expect(page.get_by_role("button", name="Preview order")).to_be_disabled()
        return f"After logout the old token gets {response.status} '{response.json()['error']['message']}'"
    check("X01", "Auth", "Logged-out session cannot trade", "401; form disabled", revoked_session)


def _csrf(page):
    """Open /trade and read the session-bound CSRF token the order form uses."""
    scheme, _, host = page.url.split("/", 3)[:3]
    page.goto(f"{scheme}//{host}/trade")
    return {"X-CSRF-Token": page.locator('meta[name="csrf-token"]').get_attribute("content")}


def _states(audit, browser, empty_base, broken_base):
    page = browser.new_page()
    page.set_default_timeout(TIMEOUT_MS)

    def empty_market():
        page.goto(f"{empty_base}/market")
        expect(page.get_by_role("heading", name="No quotes yet")).to_be_visible()
        return "/market with no quotes: 'No quotes yet'"
    audit.check("S01", "US03", "Empty state: market without quotes", "No quotes yet",
                empty_market, page, "market-empty")

    def broken_market():
        response = page.goto(f"{broken_base}/market")
        expect(page.get_by_role("alert")).to_contain_text("Market data is unavailable")
        return f"HTTP {response.status}: 'Market data is unavailable' (missing database)"
    audit.check("S02", "US03", "Error state: market database unavailable",
                "Visible error, no stack trace", broken_market, page, "market-error")

    page.close()


def _layout_and_keyboard(audit, page, base):
    def narrow():
        page.set_viewport_size({"width": 390, "height": 844})
        widths = {}
        for path in ("/market", "/trade", "/portfolio", "/login", "/register"):
            page.goto(f"{base}{path}")
            widths[path] = page.evaluate("document.documentElement.scrollWidth")
        page.goto(f"{base}/portfolio")
        assert all(width <= 390 for width in widths.values()), widths
        return f"No page-level horizontal scroll at 390 px: {widths}"
    audit.check("X02", "All", "Narrow viewport (390 px)", "scrollWidth <= 390 on every page",
                narrow, page, "narrow-portfolio")

    def keyboard():
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{base}/trade")
        reached = []
        for _ in range(8):
            page.keyboard.press("Tab")
            reached.append(page.evaluate("document.activeElement.id || document.activeElement.innerText"))
        for needed in ("symbol", "quantity", "preview-button"):
            assert needed in reached, reached
        for label in ("Stock symbol", "Number of shares"):
            expect(page.get_by_label(label)).to_be_visible()
        return f"Tab order on /trade: {[item.strip()[:18] for item in reached]}; inputs labelled"
    audit.check("X03", "All", "Keyboard navigation and labels", "Tab reaches every control",
                keyboard)


def write_report(audit, evidence_dir):
    failed = [item for item in audit.results if item["result"] == "FAIL"]
    meta = {
        "commit": _commit(),
        "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "browser": getattr(audit, "browser", "unknown"),
        "passed": len(audit.results) - len(failed),
        "failed": len(failed),
    }
    if evidence_dir is None:
        return meta
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "p0-results.json").write_text(
        json.dumps({"meta": meta, "results": audit.results}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    lines = [
        "# P0 audit results (generated)", "",
        (f"Commit `{meta['commit']}` · {meta['run_at_utc']} · Python {meta['python']} · "
         f"{meta['platform']} · {meta['browser']}"), "",
        (f"**{meta['passed']} passed, {meta['failed']} failed.** Generated by "
         "`scripts/check_p0_journeys.py`; do not edit by hand."), "",
        "| ID | Story | Check | Expected | Observed | Result | Evidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in audit.results:
        observed = item["observed"].replace("|", "\\|").replace("\n", " ")
        link = f"[png]({item['screenshot']})" if item["screenshot"] else ""
        lines.append(f"| {item['id']} | {item['story']} | {item['check']} | {item['expected']} | "
                     f"{observed} | {item['result']} | {link} |")
    (evidence_dir / "p0-results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return meta


def main():
    # Git Bash on Windows pipes stdout as cp1252; observed text contains "…" and "·".
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--evidence-dir", type=Path, help="Save screenshots and p0-results.{json,md}")
    parser.add_argument("--browser", choices=("msedge", "chrome", "chromium"), default="msedge")
    parser.add_argument("--executable-path", help="Browser binary, overriding --browser's channel")
    args = parser.parse_args()
    audit = Audit(args.evidence_dir)
    run(audit, args.browser, args.executable_path)
    meta = write_report(audit, args.evidence_dir)
    print(f"\n{meta['passed']} passed, {meta['failed']} failed · commit {meta['commit']} · "
          f"{meta['browser']} · {meta['platform']}")
    return 1 if meta["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())