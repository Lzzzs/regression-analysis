#!/usr/bin/env python3
"""Fetch 3 years of daily crypto prices from Binance and write to CSV."""
import csv
import time
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    raise SystemExit("pip install requests")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
OUT = Path(__file__).resolve().parent.parent / "data" / "providers" / "crypto_prices.csv"
START = date.today() - timedelta(days=3 * 365)
END = date.today() - timedelta(days=1)
URL = "https://api.binance.com/api/v3/klines"


def fetch_klines(symbol: str, start: date, end: date) -> list[dict]:
    rows = []
    start_ms = int(datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.combine(end, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp() * 1000) + 86400000 - 1
    cursor = start_ms
    while cursor <= end_ms:
        resp = requests.get(URL, params={"symbol": symbol, "interval": "1d", "startTime": cursor, "endTime": end_ms, "limit": 1000}, timeout=30)
        resp.raise_for_status()
        klines = resp.json()
        if not klines:
            break
        for k in klines:
            day = date.fromtimestamp(k[0] / 1000)
            rows.append({"symbol": symbol, "day": day.isoformat(), "close": float(k[4]), "source": "binance"})
        cursor = klines[-1][0] + 86400000
        time.sleep(0.2)
    return rows


def main():
    all_rows = []
    for sym in SYMBOLS:
        print(f"Fetching {sym}...")
        all_rows.extend(fetch_klines(sym, START, END))
    all_rows.sort(key=lambda r: (r["symbol"], r["day"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "day", "close", "source"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"Wrote {len(all_rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
