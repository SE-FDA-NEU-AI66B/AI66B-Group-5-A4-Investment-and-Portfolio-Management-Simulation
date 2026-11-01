"""Browser regression check for the #125 Market keyboard-focus refresh bug."""

import argparse
import tempfile
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from virtutrade.app import create_app
from virtutrade.database import init_database


def main(evidence_dir=None):
    with tempfile.TemporaryDirectory(prefix="market-keyboard-focus-") as temporary:
        database = Path(temporary) / "market.db"
        init_database(database)
        app = create_app({"TESTING": True, "DATABASE": str(database)})
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                quote_methods = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on(
                    "request",
                    lambda request: quote_methods.append(request.method)
                    if "/api/market/quotes" in request.url
                    else None,
                )
                page.goto(f"http://127.0.0.1:{server.server_port}/market?q=HPG")
                expect(page.locator("#quote-rows")).to_contain_text("HPG")
                expect(page.locator("#market-query")).to_have_value("HPG")

                status = page.locator("#refresh-status")
                for selector in (
                    "#quote-rows a.quote-link",
                    "#quote-rows a.row-action",
                    "#ticker-strip a.ticker-tile",
                    "#market-query",
                ):
                    target = page.locator(selector).first
                    with page.expect_response(
                        lambda response: "/api/market/quotes" in response.url
                        and response.request.method == "GET",
                        timeout=8000,
                    ):
                        target.focus()
                        if selector == "#market-query":
                            target.evaluate("element => element.setSelectionRange(1, 2)")
                    expect(status).to_contain_text("Snapshot refreshed", timeout=8000)
                    expect(target).to_be_focused()
                    if selector == "#market-query":
                        assert target.evaluate(
                            "element => [element.selectionStart, element.selectionEnd]"
                        ) == [1, 2]

                focus_target = page.locator("#quote-rows a.row-action").first
                for width, height in ((1440, 1000), (390, 844)):
                    page.set_viewport_size({"width": width, "height": height})
                    with page.expect_response(
                        lambda response: "/api/market/quotes" in response.url
                        and response.request.method == "GET",
                        timeout=8000,
                    ):
                        focus_target.focus()
                    expect(focus_target).to_be_focused()
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth"
                    )
                    if evidence_dir:
                        evidence_dir.mkdir(parents=True, exist_ok=True)
                        page.screenshot(
                            path=str(evidence_dir / f"market-keyboard-focus-{width}.png"),
                            full_page=True,
                        )

                def unavailable(route):
                    assert route.request.method == "GET"
                    route.fulfill(
                        status=503,
                        content_type="application/json",
                        body='{"error":{"code":"MARKET_UNAVAILABLE"}}',
                    )

                for width, height in ((1440, 1000), (390, 844)):
                    page.set_viewport_size({"width": width, "height": height})
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth"
                    )
                    snapshot = page.locator("#quote-rows").inner_text()
                    quoted_at = page.locator("#quote-rows time").get_attribute("datetime")
                    source = page.locator("#quote-rows .source").inner_text()
                    page.route("**/api/market/quotes*", unavailable)
                    with page.expect_response(
                        lambda response: "/api/market/quotes" in response.url
                        and response.request.method == "GET"
                        and response.status == 503,
                        timeout=8000,
                    ):
                        page.wait_for_timeout(3500)
                    expect(status).to_contain_text("Could not refresh", timeout=8000)
                    expect(page.get_by_role("button", name="Try again")).to_be_visible()
                    expect(page.locator("#market-query")).to_have_value("HPG")
                    assert page.locator("#quote-rows").inner_text() == snapshot
                    assert page.locator("#quote-rows time").get_attribute("datetime") == quoted_at
                    assert page.locator("#quote-rows .source").inner_text() == source
                    if evidence_dir:
                        page.screenshot(
                            path=str(evidence_dir / f"market-error-{width}.png"),
                            full_page=True,
                        )

                    page.unroute("**/api/market/quotes*", unavailable)
                    with page.expect_response(
                        lambda response: "/api/market/quotes" in response.url
                        and response.request.method == "GET"
                        and response.status == 200,
                        timeout=8000,
                    ):
                        page.get_by_role("button", name="Try again").click()
                    expect(status).to_contain_text("Snapshot refreshed", timeout=8000)
                    expect(page.locator("#retry-market")).to_be_hidden()
                    expect(page.locator("#market-query")).to_have_value("HPG")

                assert "GET" in quote_methods and "POST" not in quote_methods
                assert not errors, errors
                browser.close()
            print(
                "PASS: Market row/watchboard/Search focus survives polling; "
                "only quote GETs are sent."
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path)
    main(parser.parse_args().evidence_dir)
