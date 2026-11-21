"""Browser release gates for AI Market Watch. See --help for deployed and live checks."""
import argparse
import functools
import http.server
import json
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SYMBOLS = {s: "NASDAQ" for s in ("NVDA", "AMD", "AVGO", "GOOGL", "MSFT", "AMZN", "PLTR")}
SYMBOLS["IBM"] = "NYSE"
# The stand-in only reports what the application sent and creates the normal iframe load signal.
STUB = """
(() => {
const script = document.currentScript;
const frame = document.createElement('iframe');
frame.title = 'Market widget test fixture';
frame.style.width = '100%';
frame.style.height = '100%';
frame.srcdoc = '<html lang="en"><title>Market widget fixture</title><body>Widget loaded</body></html>';
frame.dataset.config = script.textContent;
script.parentNode.insertBefore(frame, script);
})();
"""


class StaticHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if not self.path.startswith("/ai-market-watch/"):
            self.send_error(404)
            return
        self.path = self.path[len("/ai-market-watch"):]
        super().do_GET()


@contextmanager
def target_url(url):
    if url:
        yield url.rstrip("/") + "/"
        return
    if not (ROOT / "public/index.html").is_file():
        raise SystemExit("public/index.html is missing")
    handler = functools.partial(StaticHandler, directory=str(ROOT / "public"))
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/ai-market-watch/"
        finally:
            server.shutdown()


def widget_config(page, selector):
    frame = page.locator(selector + " iframe[data-config]").first
    expect(frame).to_be_attached()
    return json.loads(frame.get_attribute("data-config"))


def has_symbol(data, symbol):
    instrument = f"{SYMBOLS[symbol]}:{symbol}"
    return re.search(re.escape(instrument) + r'(?:\||")', json.dumps(data)) is not None


def watchlist(page):
    return page.locator(".stock:visible")


def offline_checks(browser, url):
    context = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = context.new_page()
    uncaught = []
    bad_assets = []
    upstream = []
    blocked = False

    def intercept(route):
        parsed = urlparse(route.request.url)
        if parsed.netloc == urlparse(url).netloc:
            route.continue_()
        elif parsed.hostname == "s3.tradingview.com" and "/external-embedding/embed-widget-" in parsed.path:
            upstream.append(parsed.path)
            if blocked:
                route.abort()
            else:
                route.fulfill(content_type="application/javascript", body=STUB)
        else:
            route.abort()

    page.route("**/*", intercept)
    page.on("pageerror", lambda error: uncaught.append(str(error)))
    page.on("response", lambda response: bad_assets.append(response.url) if
            urlparse(response.url).netloc == urlparse(url).netloc and response.status >= 400 else None)
    page.goto(url, wait_until="domcontentloaded")
    expect(watchlist(page)).to_have_count(8)
    assert has_symbol(widget_config(page, "#chart"), "NVDA"), "Default chart must be NVIDIA"
    quote_config = widget_config(page, "#quotes")
    for symbol in SYMBOLS:
        assert has_symbol(quote_config, symbol), f"Incorrect quote exchange or symbol for {symbol}"
        page.select_option("#company", symbol)
        assert has_symbol(widget_config(page, "#chart"), symbol), f"Wrong chart for {symbol}"

    page.select_option("#group", "chips")
    expect(watchlist(page)).to_have_count(3)
    config = widget_config(page, "#quotes")
    assert {s for s in SYMBOLS if has_symbol(config, s)} == {"NVDA", "AVGO", "AMD"}
    page.fill("#search", "broad")
    expect(watchlist(page)).to_have_count(1)
    watchlist(page).click()
    expect(page.locator("#company")).to_have_value("AVGO")
    page.fill("#search", "zzmissing")
    expect(watchlist(page)).to_have_count(0)
    page.get_by_role("button", name="Clear search").click()
    expect(page.locator("#search")).to_be_focused()
    page.locator("#refresh").focus()
    before = len(upstream)
    page.keyboard.press("Enter")
    page.wait_for_function("document.querySelector('#chart iframe[data-config]') !== null")
    assert len(upstream) >= before + 2, "Refresh must reload both external widgets"
    expect(page.locator("#company")).to_have_value("AVGO")
    page.reload(wait_until="domcontentloaded")
    expect(page.locator("#company")).to_have_value("AVGO")
    expect(page.locator("#group")).to_have_value("chips")

    for width in (320, 390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 850})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow at {width}px"
        expect(page.locator("#refresh")).to_be_visible()
    blocked = True
    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_text(re.compile("unavailable", re.I)).first).to_be_visible(timeout=20000)
    assert page.locator('a[href*="tradingview.com"]:visible').count(), "Missing provider fallback link"
    blocked = False
    page.click("#refresh")
    assert has_symbol(widget_config(page, "#chart"), "AVGO"), "Retry must recover the previous company"
    # Two eligible peers and a negative outlier exercise even median, breadth,
    # abs-magnitude leader, missing coverage, and preserving a last good snapshot.
    fixture = {"date": "2024-01-05", "previousDate": "2024-01-04", "changes": {"NVDA": 2, "AMD": -6}}
    page.route("**/metrics.json", lambda route: route.fulfill(json=fixture))
    page.click("#refresh")
    expect(page.locator("#median")).to_have_text("-2.00%")
    expect(page.locator("#leader")).to_have_text("AMD -6.00%")
    expect(page.locator("#breadth")).to_have_text("1 / 2")
    expect(page.locator("#coverage")).to_contain_text("2 of 3")
    expect(page.locator("#basis")).to_contain_text("Older")
    fixture["changes"] = {}
    page.click("#refresh")
    expect(page.locator("#status")).to_contain_text("unavailable")
    expect(page.locator("#median")).to_have_text("-2.00%")
    page.set_viewport_size({"width": 640, "height": 900})
    page.evaluate("document.body.style.zoom = 2")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Overflow with 200% zoom"
    assert not uncaught, uncaught
    assert not bad_assets, bad_assets
    context.close()
    context = browser.new_context()
    context.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new Error('Storage denied')}})")
    page = context.new_page()
    page.route("**/embed-widget-*.js", lambda route: route.fulfill(content_type="application/javascript", body=STUB))
    page.goto(url, wait_until="domcontentloaded")
    page.select_option("#company", "IBM")
    assert has_symbol(widget_config(page, "#chart"), "IBM"), "Disabled storage must not break company selection"
    context.close()
    print("PASS: eight instruments, sectors, search, quote integration, refresh, storage, outage recovery and four viewports.")


def verify_live(browser, url):
    """Assert vendor-displayed data in its own frame; do not persist or republish prices."""
    context = browser.new_context(viewport={"width": 1440, "height": 960})
    page = context.new_page()
    failures = []
    page.on("pageerror", lambda error: failures.append(str(error)))
    response = page.goto(url, wait_until="domcontentloaded")
    assert response is not None and response.ok, "Dashboard document is not reachable"
    expect(page.locator("footer")).to_contain_text("v10.0")
    quotes = page.frame_locator("#quotes iframe").first.locator("body")
    aliases = dict(NVDA="NVIDIA", AMD="Advanced Micro Devices", AVGO="Broadcom", MSFT="Microsoft",
                   GOOGL="Alphabet", AMZN="Amazon", IBM="International Business Machines", PLTR="Palantir")
    for symbol, alias in aliases.items():
        # Accept either the symbol or the site's configured display name, followed by the
        # value on the next line. A standalone symbol, loading frame, or placeholder fails.
        row = re.compile(rf"(?:{symbol}|{alias}[^\n]*)\s*\n(?:US\$|\$)?[\d,]+\.\d+", re.I)
        expect(quotes).to_have_text(row, use_inner_text=True, timeout=45000)
        page.select_option("#company", symbol)
        frame = page.frame_locator("#chart iframe").first
        expect(frame.locator("body")).to_contain_text(re.compile(alias, re.I), timeout=45000)
        expect(frame.locator("body")).to_have_text(
            re.compile(r"(?:US\$|\$)?[\d,]+\.\d+\s+(?:[DR]\s+)?USD\b"),
            use_inner_text=True, timeout=45000)
        expect(frame.get_by_text("1M", exact=True).first).to_be_visible(timeout=15000)
        assert page.locator("#chart iframe").first.evaluate(
            "(f) => ['www.tradingview-widget.com','www.tradingview.com'].includes(new URL(f.src).hostname)"
        ), "Unexpected chart origin"
        print(f"PASS: vendor-displayed quote, USD chart and range controls for {symbol}", flush=True)
    assert not failures, failures
    context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Public production URL (default: serve public/ under a project subpath)")
    parser.add_argument("--channel", help="Optional installed browser channel, e.g. chrome")
    parser.add_argument("--live", action="store_true", help="Verify actual embedded vendor data")
    args = parser.parse_args()
    with target_url(args.url) as url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel)
        try:
            if args.live:
                verify_live(browser, url)
            else:
                offline_checks(browser, url)
        finally:
            browser.close()


if __name__ == "__main__":
    main()

