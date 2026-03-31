# Fix Main Flow Blockers — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 blocking bugs so the core flow works end-to-end: select assets → submit backtest → see equity curve and metrics.

**Architecture:** Replace broken akshare crypto_hist with Binance public API + CSV fallback. Add ETF data to A-share search. Make backtest engine tolerate minor price gaps via backward lookback. Auto-align end dates to Friday in the backend, remove the restriction from the frontend.

**Tech Stack:** Python 3.10+, FastAPI, Next.js 14, akshare, Binance public REST API, CSV

---

### Task 1: BinancePriceProvider — Crypto Data Source

**Files:**
- Modify: `src/portfolio_lab/data_adapters.py:347-352` (replace crypto branch)
- Test: `tests/test_binance_provider.py` (new)

- [ ] **Step 1: Write failing test for BinancePriceProvider**

Create `tests/test_binance_provider.py`:

```python
"""Tests for BinancePriceProvider."""
from datetime import date
from unittest.mock import patch, MagicMock
import json

from portfolio_lab.data_adapters import BinancePriceProvider


def _mock_klines_response(days: int = 3, start_price: float = 30000.0):
    """Build a fake Binance klines JSON response."""
    base_ts = 1704067200000  # 2024-01-01 00:00 UTC
    day_ms = 86400000
    return [
        [
            base_ts + i * day_ms,   # open time
            str(start_price + i),   # open
            str(start_price + i + 100),  # high
            str(start_price + i - 100),  # low
            str(start_price + i * 10),   # close
            "100.0",                # volume
            base_ts + (i + 1) * day_ms - 1,  # close time
            "3000000", 100, "50.0", "1500000", "0",
        ]
        for i in range(days)
    ]


class TestBinancePriceProvider:
    def test_fetch_maps_symbol_and_returns_rows(self):
        provider = BinancePriceProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _mock_klines_response(3)

        with patch("portfolio_lab.data_adapters.requests.get", return_value=mock_resp) as mock_get:
            rows = provider.fetch_price_rows(date(2024, 1, 1), date(2024, 1, 3), "BTC")

        assert len(rows) == 3
        assert rows[0]["source"] == "binance"
        assert rows[0]["close"] == 30000.0  # first close = 30000 + 0*10
        assert isinstance(rows[0]["day"], date)
        # Verify symbol mapping: BTC -> BTCUSDT
        call_url = mock_get.call_args[0][0]
        assert "BTCUSDT" in call_url

    def test_fetch_symbol_already_has_usdt_suffix(self):
        provider = BinancePriceProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _mock_klines_response(1)

        with patch("portfolio_lab.data_adapters.requests.get", return_value=mock_resp) as mock_get:
            rows = provider.fetch_price_rows(date(2024, 1, 1), date(2024, 1, 1), "BTCUSDT")

        call_url = mock_get.call_args[0][0]
        assert "BTCUSDT" in call_url
        assert "BTCUSDTUSDT" not in call_url

    def test_fetch_falls_back_to_csv_on_api_failure(self):
        provider = BinancePriceProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("portfolio_lab.data_adapters.requests.get", return_value=mock_resp):
            with patch.object(provider, "_fallback_csv") as mock_csv:
                mock_csv.return_value = [{"day": date(2024, 1, 1), "close": 42000.0, "source": "crypto-csv"}]
                rows = provider.fetch_price_rows(date(2024, 1, 1), date(2024, 1, 1), "BTC")

        assert len(rows) == 1
        assert rows[0]["source"] == "crypto-csv"

    def test_fetch_falls_back_on_network_error(self):
        provider = BinancePriceProvider()

        with patch("portfolio_lab.data_adapters.requests.get", side_effect=Exception("timeout")):
            with patch.object(provider, "_fallback_csv") as mock_csv:
                mock_csv.return_value = []
                rows = provider.fetch_price_rows(date(2024, 1, 1), date(2024, 1, 1), "BTC")

        assert rows == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lzzzs/Desktop/code/regression-analysis && PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_binance_provider.py -v`
Expected: FAIL — `ImportError: cannot import name 'BinancePriceProvider'`

- [ ] **Step 3: Implement BinancePriceProvider**

In `src/portfolio_lab/data_adapters.py`, add after the `import` block (before `class MarketDataAdapter`):

```python
try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore[assignment]
```

Then add the class before `class AKSharePriceProvider`:

```python
class BinancePriceProvider:
    """Fetch crypto daily prices from Binance public API, CSV fallback."""

    name = "binance"

    _BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
    _CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "providers" / "crypto_prices.csv"

    def _to_binance_symbol(self, symbol: str) -> str:
        s = symbol.upper()
        if not s.endswith("USDT"):
            s = s + "USDT"
        return s

    def _fallback_csv(self, start_date: date, end_date: date, symbol: str) -> list[dict]:
        csv_provider = LocalCSVPriceProvider(self._CSV_PATH, name="crypto-csv")
        binance_symbol = self._to_binance_symbol(symbol)
        return csv_provider.fetch_price_rows(start_date, end_date, binance_symbol)

    def fetch_price_rows(self, start_date: date, end_date: date, symbol: str) -> list[dict]:
        if _requests is None:
            return self._fallback_csv(start_date, end_date, symbol)

        binance_symbol = self._to_binance_symbol(symbol)
        start_ms = int(datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp() * 1000)
        end_ms = int(datetime.combine(end_date, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp() * 1000) + 86400000 - 1

        all_rows: list[dict] = []
        cursor = start_ms
        try:
            while cursor <= end_ms:
                resp = _requests.get(
                    self._BINANCE_KLINES_URL,
                    params={"symbol": binance_symbol, "interval": "1d", "startTime": cursor, "endTime": end_ms, "limit": 1000},
                    timeout=15,
                )
                if resp.status_code != 200:
                    return self._fallback_csv(start_date, end_date, symbol)
                klines = resp.json()
                if not klines:
                    break
                for k in klines:
                    day = date.fromtimestamp(k[0] / 1000)
                    close = float(k[4])
                    all_rows.append({"day": day, "close": close, "source": "binance"})
                cursor = klines[-1][0] + 86400000
        except Exception:
            return self._fallback_csv(start_date, end_date, symbol)

        return all_rows if all_rows else self._fallback_csv(start_date, end_date, symbol)
```

Note: this needs `from datetime import datetime, timezone` at the top — already imported in `backtest.py` but `data_adapters.py` only imports `date`. Add `datetime, timezone` to the import.

- [ ] **Step 4: Update AKSharePriceProvider to remove crypto branch**

In `src/portfolio_lab/data_adapters.py`, replace lines 347-352 (the `elif self.market == "crypto":` branch):

```python
            elif self.market == "crypto":
                raise ValidationError("crypto market should use BinancePriceProvider, not AKSharePriceProvider")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/lzzzs/Desktop/code/regression-analysis && PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_binance_provider.py -v`
Expected: all 4 tests PASS

- [ ] **Step 6: Create seed script and expand crypto CSV**

Create `scripts/seed_crypto_csv.py`:

```python
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
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "day", "close", "source"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"Wrote {len(all_rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
```

Run: `cd /Users/lzzzs/Desktop/code/regression-analysis && .venv/bin/pip install requests && .venv/bin/python scripts/seed_crypto_csv.py`

- [ ] **Step 7: Commit**

```bash
git add src/portfolio_lab/data_adapters.py tests/test_binance_provider.py scripts/seed_crypto_csv.py data/providers/crypto_prices.csv
git commit -m "feat: replace broken akshare crypto_hist with Binance API + CSV fallback"
```

---

### Task 2: A-Share Search — Include ETFs + Fallback

**Files:**
- Modify: `apps/api/asset_router.py:103-127, 186-199`
- Test: `tests/test_asset_search.py` (new)

- [ ] **Step 1: Write failing test**

Create `tests/test_asset_search.py`:

```python
"""Tests for asset search including ETFs and fallback."""
from unittest.mock import patch, MagicMock
import pandas as pd

from apps.api.asset_router import _fetch_cn_items, _FALLBACK_CN_ITEMS


class TestFetchCnItems:
    def test_includes_etfs_from_stock_list(self):
        """510300 starts with '5' so it should be tagged as ETF."""
        stock_df = pd.DataFrame({"code": ["000001", "510300"], "name": ["平安银行", "沪深300ETF"]})
        etf_df = pd.DataFrame({"代码": ["159915"], "名称": ["创业板ETF"]})

        with patch("apps.api.asset_router.ak") as mock_ak:
            mock_ak.stock_info_a_code_name.return_value = stock_df
            mock_ak.fund_etf_spot_em.return_value = etf_df
            items = _fetch_cn_items()

        codes = [item["code"] for item in items]
        assert "510300" in codes
        assert "159915" in codes
        assert "000001" in codes

    def test_search_filters_by_code(self):
        """Searching '510300' should find it in the list."""
        stock_df = pd.DataFrame({"code": ["000001", "510300"], "name": ["平安银行", "沪深300ETF"]})
        etf_df = pd.DataFrame({"代码": ["159915"], "名称": ["创业板ETF"]})

        with patch("apps.api.asset_router.ak") as mock_ak:
            mock_ak.stock_info_a_code_name.return_value = stock_df
            mock_ak.fund_etf_spot_em.return_value = etf_df
            items = _fetch_cn_items()

        q = "510300"
        filtered = [i for i in items if q in i["code"].lower() or q in i["name"].lower()]
        assert len(filtered) == 1
        assert filtered[0]["code"] == "510300"

    def test_fallback_when_akshare_unavailable(self):
        """When ak is None, should return fallback list."""
        with patch("apps.api.asset_router.ak", None):
            items = _fetch_cn_items()

        assert len(items) > 0
        codes = [i["code"] for i in items]
        assert "510300" in codes  # CSI300 ETF must be in fallback


class TestFallbackList:
    def test_fallback_has_common_assets(self):
        assert any(i["code"] == "510300" for i in _FALLBACK_CN_ITEMS)
        assert any(i["code"] == "000001" for i in _FALLBACK_CN_ITEMS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lzzzs/Desktop/code/regression-analysis && PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_asset_search.py -v`
Expected: FAIL — `ImportError: cannot import name '_FALLBACK_CN_ITEMS'`

- [ ] **Step 3: Add fallback list and update _fetch_cn_items**

In `apps/api/asset_router.py`, add before `_cn_cache` (after line 37):

```python
_FALLBACK_CN_ITEMS: list[dict] = [
    {"code": "000001", "name": "平安银行", "market": "cn", "asset_type": "stock"},
    {"code": "000002", "name": "万科A", "market": "cn", "asset_type": "stock"},
    {"code": "000300", "name": "沪深300", "market": "cn", "asset_type": "index"},
    {"code": "600519", "name": "贵州茅台", "market": "cn", "asset_type": "stock"},
    {"code": "601318", "name": "中国平安", "market": "cn", "asset_type": "stock"},
    {"code": "600036", "name": "招商银行", "market": "cn", "asset_type": "stock"},
    {"code": "000858", "name": "五粮液", "market": "cn", "asset_type": "stock"},
    {"code": "601012", "name": "隆基绿能", "market": "cn", "asset_type": "stock"},
    {"code": "600900", "name": "长江电力", "market": "cn", "asset_type": "stock"},
    {"code": "601888", "name": "中国中免", "market": "cn", "asset_type": "stock"},
    {"code": "510300", "name": "沪深300ETF", "market": "cn", "asset_type": "etf"},
    {"code": "510500", "name": "中证500ETF", "market": "cn", "asset_type": "etf"},
    {"code": "510050", "name": "上证50ETF", "market": "cn", "asset_type": "etf"},
    {"code": "159919", "name": "沪深300ETF", "market": "cn", "asset_type": "etf"},
    {"code": "159915", "name": "创业板ETF", "market": "cn", "asset_type": "etf"},
    {"code": "513100", "name": "纳指ETF", "market": "cn", "asset_type": "etf"},
    {"code": "518880", "name": "黄金ETF", "market": "cn", "asset_type": "etf"},
    {"code": "511010", "name": "国债ETF", "market": "cn", "asset_type": "etf"},
    {"code": "513050", "name": "中概互联ETF", "market": "cn", "asset_type": "etf"},
    {"code": "512690", "name": "酒ETF", "market": "cn", "asset_type": "etf"},
]
```

Then replace `_fetch_cn_items()` (lines 103-127):

```python
def _fetch_cn_items() -> list[dict]:
    if ak is None:
        return list(_FALLBACK_CN_ITEMS)
    try:
        stocks_df = ak.stock_info_a_code_name()
        code_col = _col(stocks_df, "code", "代码")
        name_col = _col(stocks_df, "name", "名称")
        items: list[dict] = []
        for _, row in stocks_df.iterrows():
            code = str(row[code_col]).strip()
            asset_type = "etf" if (code.startswith("5") or code.startswith("159")) else "stock"
            items.append({"code": code, "name": str(row[name_col]).strip(), "market": "cn", "asset_type": asset_type})
        # Supplement with dedicated ETF list
        try:
            etf_df = ak.fund_etf_spot_em()
            etf_code_col = _col(etf_df, "代码", "code")
            etf_name_col = _col(etf_df, "名称", "name")
            existing_codes = {item["code"] for item in items}
            for _, row in etf_df.iterrows():
                code = str(row[etf_code_col]).strip()
                if code not in existing_codes:
                    items.append({"code": code, "name": str(row[etf_name_col]).strip(), "market": "cn", "asset_type": "etf"})
        except Exception:
            pass
        return items
    except Exception:
        return list(_FALLBACK_CN_ITEMS)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/lzzzs/Desktop/code/regression-analysis && PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_asset_search.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/asset_router.py tests/test_asset_search.py
git commit -m "feat: include ETFs in A-share search, add fallback asset list"
```

---

### Task 3: Backtest Missing Price Tolerance

**Files:**
- Modify: `src/portfolio_lab/backtest.py:121-140`
- Test: `tests/test_price_tolerance.py` (new)

- [ ] **Step 1: Write failing test**

Create `tests/test_price_tolerance.py`:

```python
"""Tests for backtest price gap tolerance."""
from datetime import date

from portfolio_lab.backtest import BacktestEngine
from portfolio_lab.models import CalendarType


class TestResolvePriceTolerance:
    def setup_method(self):
        self.engine = BacktestEngine(data_dir="/tmp/test_backtest_data")
        self.asset = {
            "identifier": "000001",
            "asset_type": "stock",
            "market": "CN",
            "calendar": "a_share",
            "quote_currency": "CNY",
        }

    def test_exact_match_returns_price(self):
        prices = {"2024-01-02": {"close": 10.0}}
        price, stale, closed = self.engine._resolve_asset_price(self.asset, prices, date(2024, 1, 2))
        assert price == 10.0
        assert stale is False

    def test_trading_day_gap_uses_lookback(self):
        """Monday 2024-01-08 is missing but Friday 2024-01-05 has data — should lookback."""
        prices = {"2024-01-05": {"close": 10.5}}
        price, stale, closed = self.engine._resolve_asset_price(self.asset, prices, date(2024, 1, 8))
        assert price == 10.5
        assert stale is True

    def test_trading_day_gap_beyond_5_days_raises(self):
        """If no price within 5 lookback days, should raise."""
        prices = {"2023-12-25": {"close": 10.0}}  # too far back
        import pytest
        with pytest.raises(Exception, match="missing price"):
            self.engine._resolve_asset_price(self.asset, prices, date(2024, 1, 8))

    def test_weekend_uses_last_known(self):
        """Weekend should use last known price (existing behavior)."""
        prices = {"2024-01-05": {"close": 10.5}}
        price, stale, closed = self.engine._resolve_asset_price(self.asset, prices, date(2024, 1, 6))
        assert price == 10.5
        assert stale is True
        assert closed is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lzzzs/Desktop/code/regression-analysis && PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_price_tolerance.py -v`
Expected: `test_trading_day_gap_uses_lookback` FAILS with `MissingDataError`

- [ ] **Step 3: Update _resolve_asset_price with lookback logic**

In `src/portfolio_lab/backtest.py`, replace `_resolve_asset_price` (lines 121-140):

```python
    def _resolve_asset_price(
        self,
        asset: AssetDefinition,
        price_series: dict,
        day: date,
    ) -> tuple[float, bool, bool]:
        """Return (price, is_stale, market_closed).

        On a trading day with no price, look back up to 5 days for the most
        recent known price and mark it stale.  Raise only when no price exists
        within the lookback window.
        """
        day_key = day.isoformat()
        if day_key in price_series:
            return float(price_series[day_key]["close"]), False, False

        trading_day = is_trading_day(day, CalendarType(asset["calendar"]))

        # Look backward for the most recent price
        previous_days = sorted(d for d in price_series.keys() if d < day_key)
        if previous_days:
            last_day = previous_days[-1]
            gap = (day - date.fromisoformat(last_day)).days
            if trading_day and gap > 5:
                raise MissingDataError(
                    f"missing price on expected trading day (no data within 5-day lookback): "
                    f"{asset['identifier']} {day_key}"
                )
            return float(price_series[last_day]["close"]), True, not trading_day

        if trading_day:
            raise MissingDataError(f"missing price on expected trading day: {asset['identifier']} {day_key}")

        raise MissingDataError(f"no historical close for stale valuation: {asset['identifier']} {day_key}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/lzzzs/Desktop/code/regression-analysis && PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_price_tolerance.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/portfolio_lab/backtest.py tests/test_price_tolerance.py
git commit -m "feat: tolerate minor price gaps with 5-day backward lookback"
```

---

### Task 4: Auto-Align End Date to Friday

**Files:**
- Modify: `apps/api/orchestration.py:62-63`
- Modify: `apps/web/app/page.tsx:10-17, 29-30, 65-67, 201`
- Test: `tests/test_friday_alignment.py` (new)

- [ ] **Step 1: Write failing test for backend auto-alignment**

Create `tests/test_friday_alignment.py`:

```python
"""Tests for auto-aligning end_date to Friday."""
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from apps.api.orchestration import AutoJobOrchestrator


def _align_to_friday(d: date) -> date:
    """Expected behavior: roll back to most recent Friday on or before d."""
    while d.weekday() != 4:
        d -= timedelta(days=1)
    return d


class TestFridayAutoAlign:
    def test_wednesday_aligns_to_previous_friday(self):
        # 2026-03-25 is Wednesday -> should become 2026-03-20 (Friday)
        assert _align_to_friday(date(2026, 3, 25)) == date(2026, 3, 20)

    def test_friday_stays_friday(self):
        # 2026-03-27 is Friday -> stays
        assert _align_to_friday(date(2026, 3, 27)) == date(2026, 3, 27)

    def test_saturday_aligns_to_friday(self):
        # 2026-03-28 is Saturday -> 2026-03-27 (Friday)
        assert _align_to_friday(date(2026, 3, 28)) == date(2026, 3, 27)

    def test_orchestrator_no_longer_rejects_non_friday(self):
        """Submitting a Wednesday end_date should not raise ContractError."""
        mock_service = MagicMock()
        mock_snapshot_service = MagicMock()
        mock_snapshot_service.create_snapshot_from_providers.return_value = {"snapshot_id": "snap-test"}
        mock_service.create_job.return_value = {"job_id": "job-test", "status": "queued"}

        orch = AutoJobOrchestrator(mock_service, mock_snapshot_service)

        payload = {
            "weights": {"000001": 1.0},
            "start_date": "2025-03-26",
            "end_date": "2026-03-25",  # Wednesday — should NOT raise
            "rebalance_frequency": "monthly",
            "selected_assets": ["000001"],
            "assets": [{"code": "000001", "market": "cn", "asset_type": "stock"}],
        }
        # Should not raise
        result = orch.create_job_auto(payload)
        assert result["job_id"] == "job-test"

        # Verify the snapshot got the aligned Friday date
        snap_call = mock_snapshot_service.create_snapshot_from_providers.call_args[0][0]
        assert snap_call["week_end"] == "2026-03-20"  # aligned to Friday
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lzzzs/Desktop/code/regression-analysis && PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_friday_alignment.py -v`
Expected: `test_orchestrator_no_longer_rejects_non_friday` FAILS with `ContractError: 结束日期必须为周五`

- [ ] **Step 3: Update orchestration.py — replace validation with auto-alignment**

In `apps/api/orchestration.py`, add `timedelta` to the import at line 5:

```python
from datetime import date, timedelta
```

Then replace lines 62-63:

```python
        if end_date.weekday() != 4:
            raise ContractError("结束日期必须为周五（快照按周发布）")
```

With:

```python
        # Auto-align end_date to most recent Friday (on or before)
        while end_date.weekday() != 4:
            end_date -= timedelta(days=1)
        # Update request with aligned date
        request.end_date = end_date.isoformat()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/lzzzs/Desktop/code/regression-analysis && PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_friday_alignment.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Update frontend — remove Friday validation and hints**

In `apps/web/app/page.tsx`:

**5a.** Remove the `lastFriday` function (lines 10-17) and simplify defaults (lines 29-30). Replace with:

```typescript
function todayStr(): string {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d.toISOString().slice(0, 10);
}

const DEFAULT_END = todayStr();
const DEFAULT_START = dateOffset(DEFAULT_END, 1);
```

**5b.** Remove the Friday validation check (lines 65-68):

Delete these lines:
```typescript
    if (end.getUTCDay() !== 5) {
      setError('结束日期必须为周五（快照发布要求）');
      return;
    }
```

**5c.** Remove the hint text at line 201:

Change:
```tsx
<p className="text-xs text-gray-400 mt-1">结束日期需为周五</p>
```
To:
```tsx
<p className="text-xs text-gray-400 mt-1">结束日期将自动对齐到周五</p>
```

**5d.** Update preset buttons (lines 154-157) — use today instead of lastFriday:

Change:
```typescript
onClick={() => {
  setEndDate(DEFAULT_END);
  setStartDate(dateOffset(DEFAULT_END, preset.years));
}}
```

This already works since `DEFAULT_END` is now `todayStr()`.

- [ ] **Step 6: Run all tests**

Run: `cd /Users/lzzzs/Desktop/code/regression-analysis && PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_friday_alignment.py tests/test_binance_provider.py tests/test_asset_search.py tests/test_price_tolerance.py -v`
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add apps/api/orchestration.py apps/web/app/page.tsx tests/test_friday_alignment.py
git commit -m "feat: auto-align end date to Friday, remove frontend restriction"
```

---

### Task 5: Wire BinancePriceProvider into Snapshot Service

**Files:**
- Modify: `apps/api/snapshot_service.py`

- [ ] **Step 1: Update snapshot_service.py to use BinancePriceProvider for crypto**

In `apps/api/snapshot_service.py`, add `BinancePriceProvider` to the import (line 11):

```python
from portfolio_lab.data_adapters import (
    AKShareFXProvider,
    AKSharePriceProvider,
    BinancePriceProvider,
    LocalCSVFXProvider,
    LocalCSVPriceProvider,
    RoutedMarketDataAdapter,
)
```

Then find where `providers_by_market` is assembled (search for `"CRYPTO"` key assignment) and ensure it uses `BinancePriceProvider()` instead of `AKSharePriceProvider("crypto")`.

Read the full `snapshot_service.py` to find the exact location — it should be in the `build_snapshot_service` or `_build_routed_adapter` function where market→provider mapping is set up. Replace:

```python
"CRYPTO": AKSharePriceProvider("crypto"),
```

With:

```python
"CRYPTO": BinancePriceProvider(),
```

- [ ] **Step 2: Verify by running the seed script and checking API**

Run: `cd /Users/lzzzs/Desktop/code/regression-analysis && bash scripts/dev_down.sh 2>/dev/null; JOB_QUEUE_BACKEND=file bash scripts/dev_up.sh`

Wait 5 seconds then: `curl -s --noproxy '*' http://127.0.0.1:8000/health`
Expected: `{"status":"ok"}`

- [ ] **Step 3: Commit**

```bash
git add apps/api/snapshot_service.py
git commit -m "feat: wire BinancePriceProvider into snapshot service for crypto"
```

---

### Task 6: Install requests dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add requests to pyproject.toml dependencies**

In `pyproject.toml`, update the dependencies list:

```toml
dependencies = ["akshare", "requests"]
```

- [ ] **Step 2: Install and verify**

Run: `cd /Users/lzzzs/Desktop/code/regression-analysis && .venv/bin/pip install requests`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add requests to dependencies for Binance API"
```
