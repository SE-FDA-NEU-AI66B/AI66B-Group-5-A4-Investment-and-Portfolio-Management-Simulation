"""Browser QA for #78: registration shows the one-time grant and login does not add it.

Uses a disposable seeded database and real registration/login; no test identity
and no provider calls. Writes docs/images/ui/grant-balance.png as UI evidence.
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
from virtutrade.database import init_database

EVIDENCE = Path(__file__).resolve().parents[1] / "docs" / "images" / "ui"


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="grant-ui-") as tmp:
        database = Path(tmp) / "grant.db"
        init_database(database)
        app = create_app({"TESTING": True, "DATABASE": str(database),
                          "SECRET_KEY": secrets.token_hex(32)})
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        email = "grant-ui@example.test"
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
                expect(page.get_by_text(email, exact=False).first).to_be_visible()
                expect(page.get_by_text("100,000,000 VND", exact=False).first).to_be_visible()
                page.screenshot(path=str(EVIDENCE / "grant-balance.png"))

                page.get_by_role("button", name="Log out").click()
                page.get_by_role("link", name="Log in", exact=True).click()
                page.get_by_label("Email", exact=True).fill(email)
                page.get_by_label("Password", exact=False).fill(password)
                page.get_by_role("button", name="Log in", exact=True).click()
                expect(page.get_by_text("100,000,000 VND", exact=False).first).to_be_visible()

                assert not errors, errors
                browser.close()

            with closing(sqlite3.connect(database)) as connection:
                rows = connection.execute(
                    "SELECT cash_vnd FROM account WHERE email = ?", (email,)).fetchall()
                assert rows == [(100_000_000,)], rows
                assert connection.execute("SELECT COUNT(*) FROM account").fetchone()[0] == 1
            print("PASS: real registration and login show exactly 100,000,000 VND; "
                  "screenshot written to docs/images/ui/grant-balance.png.")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
