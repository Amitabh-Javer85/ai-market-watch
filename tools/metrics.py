"""Publish daily percentage changes only. Raw provider bars never leave memory."""

import argparse
import json
import math
import os
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TICKERS = ("NVDA", "AMD", "AVGO", "MSFT", "GOOGL", "AMZN", "IBM", "PLTR")
URL = "https://getmarkethistory.com/api/v1/bars/stocks/us/{}/1d"
OUTPUT = Path(__file__).resolve().parents[1] / "public" / "metrics.json"


def fetch_sample(ticker):
    request = Request(URL.format(ticker), headers={"User-Agent": "AI-Market-Watch/10.0"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read(256_001)
            if len(raw) > 256_000:
                raise ValueError(f"{ticker}: oversized sample")
            return [json.loads(line) for line in raw.splitlines() if line.strip()]
        except (HTTPError, URLError, TimeoutError) as exc:
            delay = 2 ** (attempt + 1)
            if isinstance(exc, HTTPError):
                if exc.code not in (429, 500, 502, 503, 504):
                    raise
                after = exc.headers.get("Retry-After")
                if after:
                    if not after.isdigit() or int(after) > 60:
                        raise
                    delay = max(delay, int(after))
            if attempt == 2:
                raise
            time.sleep(delay)


def recent_pair(ticker, rows, today):
    closes = {}
    for row in rows:
        if row.get("symbol") != ticker:
            raise ValueError(f"{ticker}: incorrect symbol")
        timestamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError(f"{ticker}: timezone missing")
        session = timestamp.astimezone(timezone.utc).date()
        close = row.get("close")
        if row.get("is_gap") is True or type(close) not in (int, float) or not math.isfinite(close) or close <= 0:
            raise ValueError(f"{ticker}: invalid close or gap")
        if session in closes or session >= today or session.weekday() >= 5:
            raise ValueError(f"{ticker}: duplicate or invalid session")
        closes[session] = close
    if len(closes) < 2:
        raise ValueError(f"{ticker}: insufficient data")
    prior, latest = sorted(closes)[-2:]
    if today - latest > timedelta(days=10) or latest - prior > timedelta(days=5):
        raise ValueError(f"{ticker}: stale or discontinuous sample")
    return prior, latest, round(100 * (closes[latest] / closes[prior] - 1), 4)


def build_snapshot(fetch=fetch_sample, today=None):
    today = today or datetime.now(timezone.utc).date()
    changes = {}
    session_pair = None
    for ticker in TICKERS:
        prior, latest, change = recent_pair(ticker, fetch(ticker), today)
        if session_pair is not None and session_pair != (prior, latest):
            raise ValueError(f"{ticker}: sessions differ from the rest of the watchlist")
        session_pair = prior, latest
        changes[ticker] = change
    return {
        "date": latest.isoformat(),
        "previousDate": prior.isoformat(),
        "source": "GetMarketHistory",
        "basis": "Unadjusted · includes extended hours",
        "changes": changes,
    }


def publish(snapshot, target):
    if target.exists():
        current = json.loads(target.read_text(encoding="utf-8"))
        if date.fromisoformat(snapshot["date"]) < date.fromisoformat(current["date"]):
            raise ValueError("Refusing to replace a newer snapshot")
        if current == snapshot:
            return
    target.parent.mkdir(parents=True, exist_ok=True)
    out = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, delete=False)
    temporary = Path(out.name)
    try:
        with out:
            json.dump(snapshot, out, indent=2, ensure_ascii=False, allow_nan=False)
            out.write("\n")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    target = parser.parse_args().output
    snapshot = build_snapshot()
    publish(snapshot, target)
    print(f"{len(snapshot['changes'])} verified daily changes through {snapshot['date']}")
