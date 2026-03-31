# Fix Main Flow Blockers — Design Spec

> Date: 2026-03-31
> Goal: Make the core flow work end-to-end: select assets → submit backtest → see equity curve and metrics

---

## Module 1: Crypto Data Source Replacement

### Problem
akshare 1.18.49 removed `crypto_hist`. Crypto backtest fails with `module 'akshare' has no attribute 'crypto_hist'`.

### Solution
Add `BinancePriceProvider` in `data_adapters.py` using Binance public API (`/api/v3/klines`, no API key needed). Falls back to local `crypto_prices.csv` on failure.

### Changes
- `src/portfolio_lab/data_adapters.py` — new `BinancePriceProvider` class; update `RoutedMarketDataAdapter` to route crypto to it
- `data/providers/crypto_prices.csv` — expand from 5 rows to ~5500 rows (5 coins × 3 years daily)
- `scripts/seed_crypto_csv.py` — one-time script to fetch from Binance and write CSV

### BinancePriceProvider spec
- `fetch(symbol, start_date, end_date)` → list of `{day, close, source}`
- Symbol mapping: "BTC" → "BTCUSDT", "ETH" → "ETHUSDT", etc.
- API: `GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&startTime={ms}&endTime={ms}&limit=1000`
- Paginate if range > 1000 days
- On any request failure, fall back to `LocalCSVPriceProvider` with `crypto_prices.csv`

---

## Module 2: A-Share Search Fix

### Problem
Searching "510300" returns empty. `ak.stock_info_a_code_name()` only returns stocks, not ETFs (510xxx/159xxx).

### Solution
Merge ETF data into CN asset search results. Add hardcoded fallback for when akshare fails.

### Changes
- `apps/api/asset_router.py`:
  - `_fetch_cn_items()`: also call `ak.fund_etf_spot_em()` to get ETF list, merge into results
  - Add `_FALLBACK_CN_ASSETS`: hardcoded list of ~20 popular assets (CSI300 ETF, CSI500 ETF, popular stocks) as fallback when akshare is unavailable
  - Search filters both stocks and ETFs

---

## Module 3: Backtest Missing Price Tolerance

### Problem
akshare price data has gaps on some trading days. Engine raises `MissingDataError` immediately.

### Solution
Allow forward-fill from recent prices (up to 5 trading days lookback). Fail only when data is truly missing.

### Changes
- `src/portfolio_lab/backtest.py`:
  - `_resolve_asset_price()`: on trading day with no price, search backward up to 5 days for last known price, mark as stale
  - Raise `MissingDataError` only if no price found within 5-day lookback
- `apps/api/orchestration.py`:
  - After snapshot creation, pre-check: for each asset, verify at least one price exists within 7 days of start_date. Fail early with clear error if not.

---

## Module 4: Auto-Align End Date to Friday

### Problem
Users must manually pick a Friday as end date. Bad UX. Timezone bug between `getDay()` and `getUTCDay()`.

### Solution
Backend auto-aligns end_date to the most recent Friday (on or before the given date). Frontend removes Friday validation entirely.

### Changes
- `apps/api/orchestration.py`:
  - Replace Friday validation error with auto-alignment: `while end_date.weekday() != 4: end_date -= timedelta(days=1)`
- `apps/shared/contracts.py`:
  - Remove Friday validation if present
- `apps/web/app/page.tsx`:
  - Remove `getUTCDay() !== 5` check
  - Remove "结束日期需为周五" hint text
  - Simplify date preset buttons to just compute relative dates without Friday alignment

---

## Out of Scope
- US/HK market search or backtest fixes (not tested, defer)
- Chart interactivity improvements
- Strategy templates
- Any UI redesign
