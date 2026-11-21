"""Local, read-only market dashboard. Run with python server.py."""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "snapshot.json"
SYMBOLS = "NVDA AMD AVGO MSFT GOOGL AMZN IBM PLTR".split()
lock = threading.Lock()
last_check = 0

def history(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1y&interval=1d"
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=12) as r:
        series = json.load(r)["chart"]["result"][0]
    meta = series["meta"]
    assert meta["symbol"] == symbol and meta["currency"] == "USD"
    session = meta["currentTradingPeriod"]["regular"]
    today = datetime.fromtimestamp(session["start"], timezone.utc).date().isoformat()
    values = []
    for ts, price in zip(series["timestamp"], series["indicators"]["quote"][0]["close"]):
        day = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
        if price and price > 0 and (day < today or time.time() >= session["end"]):
            if values and day == values[-1][0]:
                values.pop()
            values.append([day, round(price, 4)])
    if len(values) < 2:
        raise ValueError("Insufficient history")
    return values

def snapshot(force):
    global last_check
    with lock:
        old = json.loads(CACHE.read_text()) if CACHE.exists() else {"series": {}}
        if old["series"] and (not force or time.monotonic() - last_check < 60):
            return old
        series = old["series"].copy()
        errors = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs = {s: pool.submit(history, s) for s in SYMBOLS}
            for s, job in jobs.items():
                try:
                    series[s] = job.result()
                except Exception:
                    errors.append(s)
        last_check = time.monotonic()
        data = {"series": series, "errors": errors, "checked": datetime.now(timezone.utc).isoformat()}
        if series:
            tmp = CACHE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            tmp.replace(CACHE)
        return data

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/api/prices", "/api/refresh"):
            body = json.dumps(snapshot(self.path.endswith("refresh"))).encode()
            mime = "application/json"
        elif self.path == "/":
            body = (ROOT / "index.html").read_bytes()
            mime = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8791), Handler).serve_forever()
