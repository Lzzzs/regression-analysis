"""Market data adapter abstractions and offline implementations."""

from __future__ import annotations

import contextlib
import csv
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Protocol

try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore[assignment]

from .errors import ValidationError


class MarketDataAdapter(Protocol):
    """Adapter interface for fetching market data rows."""

    def fetch_prices(self, start_date: date, end_date: date, asset_ids: list[str]) -> list[dict]:
        """Return price rows containing asset_id/day/close/source."""

    def fetch_fx(self, start_date: date, end_date: date, pairs: list[str]) -> list[dict]:
        """Return FX rows containing pair/day/rate/source."""


class PriceDataProvider(Protocol):
    """Provider interface for fetching one symbol's price rows."""

    name: str

    def fetch_price_rows(self, start_date: date, end_date: date, symbol: str) -> list[dict]:
        """Return price rows with day/close/source."""


class FXDataProvider(Protocol):
    """Provider interface for fetching one FX pair rows."""

    name: str

    def fetch_fx_rows(self, start_date: date, end_date: date, pair: str) -> list[dict]:
        """Return FX rows with day/rate/source."""


class LocalJSONMarketDataAdapter:
    """Offline adapter backed by local JSON files."""

    def __init__(self, prices_file: str | Path, fx_file: str | Path, default_source: str = "local_fixture") -> None:
        self.prices_file = Path(prices_file)
        self.fx_file = Path(fx_file)
        self.default_source = default_source

    @staticmethod
    def _parse_day(raw: object) -> date:
        if isinstance(raw, date):
            return raw
        return date.fromisoformat(str(raw))

    @staticmethod
    def _within_range(day: date, start_date: date, end_date: date) -> bool:
        return start_date <= day <= end_date

    def fetch_prices(self, start_date: date, end_date: date, asset_ids: list[str]) -> list[dict]:
        selected = {asset_id.upper() for asset_id in asset_ids}
        raw_rows = json.loads(self.prices_file.read_text(encoding="utf-8"))
        rows: list[dict] = []
        for row in raw_rows:
            asset_id = str(row["asset_id"]).upper()
            day = self._parse_day(row["day"])
            if selected and asset_id not in selected:
                continue
            if not self._within_range(day, start_date, end_date):
                continue
            rows.append(
                {
                    "asset_id": asset_id,
                    "day": day,
                    "close": float(row["close"]),
                    "source": str(row.get("source", self.default_source)),
                }
            )
        return rows

    def fetch_fx(self, start_date: date, end_date: date, pairs: list[str]) -> list[dict]:
        selected = {pair.upper() for pair in pairs}
        raw_rows = json.loads(self.fx_file.read_text(encoding="utf-8"))
        rows: list[dict] = []
        for row in raw_rows:
            pair = str(row["pair"]).upper()
            day = self._parse_day(row["day"])
            if selected and pair not in selected:
                continue
            if not self._within_range(day, start_date, end_date):
                continue
            rows.append(
                {
                    "pair": pair,
                    "day": day,
                    "rate": float(row["rate"]),
                    "source": str(row.get("source", self.default_source)),
                }
            )
        return rows


class LocalCSVPriceProvider:
    """CSV-backed price provider with symbol/day/close/source columns."""

    def __init__(
        self,
        csv_file: str | Path,
        name: str,
        symbol_column: str = "symbol",
        day_column: str = "day",
        close_column: str = "close",
        source_column: str = "source",
    ) -> None:
        self.csv_file = Path(csv_file)
        self.name = name
        self.symbol_column = symbol_column
        self.day_column = day_column
        self.close_column = close_column
        self.source_column = source_column

    @staticmethod
    def _parse_day(raw: object) -> date:
        if isinstance(raw, date):
            return raw
        return date.fromisoformat(str(raw))

    def fetch_price_rows(self, start_date: date, end_date: date, symbol: str) -> list[dict]:
        normalized_symbol = symbol.upper()
        rows: list[dict] = []
        with self.csv_file.open("r", encoding="utf-8", newline="") as f:
            for raw in csv.DictReader(f):
                row_symbol = str(raw.get(self.symbol_column, "")).upper()
                if row_symbol != normalized_symbol:
                    continue
                day = self._parse_day(raw.get(self.day_column, ""))
                if day < start_date or day > end_date:
                    continue
                close = float(raw.get(self.close_column, "0"))
                source = str(raw.get(self.source_column, "")).strip() or self.name
                rows.append({"day": day, "close": close, "source": source})
        return rows


class LocalCSVFXProvider:
    """CSV-backed FX provider with pair/day/rate/source columns."""

    def __init__(
        self,
        csv_file: str | Path,
        name: str,
        pair_column: str = "pair",
        day_column: str = "day",
        rate_column: str = "rate",
        source_column: str = "source",
    ) -> None:
        self.csv_file = Path(csv_file)
        self.name = name
        self.pair_column = pair_column
        self.day_column = day_column
        self.rate_column = rate_column
        self.source_column = source_column

    @staticmethod
    def _parse_day(raw: object) -> date:
        if isinstance(raw, date):
            return raw
        return date.fromisoformat(str(raw))

    def fetch_fx_rows(self, start_date: date, end_date: date, pair: str) -> list[dict]:
        normalized_pair = pair.upper()
        rows: list[dict] = []
        with self.csv_file.open("r", encoding="utf-8", newline="") as f:
            for raw in csv.DictReader(f):
                row_pair = str(raw.get(self.pair_column, "")).upper()
                if row_pair != normalized_pair:
                    continue
                day = self._parse_day(raw.get(self.day_column, ""))
                if day < start_date or day > end_date:
                    continue
                rate = float(raw.get(self.rate_column, "0"))
                source = str(raw.get(self.source_column, "")).strip() or self.name
                rows.append({"day": day, "rate": rate, "source": source})
        return rows


class RoutedMarketDataAdapter:
    """Route price fetches to market-specific providers and normalize outputs."""

    def __init__(
        self,
        providers_by_market: dict[str, PriceDataProvider],
        fx_provider: FXDataProvider,
        asset_market_map: dict[str, str],
        asset_symbol_map: dict[str, str] | None = None,
    ) -> None:
        self.providers_by_market = {str(k).upper(): v for k, v in providers_by_market.items()}
        self.fx_provider = fx_provider
        self.asset_market_map = {str(k).upper(): str(v).upper() for k, v in asset_market_map.items()}
        self.asset_symbol_map = (
            {str(k).upper(): str(v).upper() for k, v in asset_symbol_map.items()} if asset_symbol_map else {}
        )

    @staticmethod
    def _parse_day(raw: object) -> date:
        if isinstance(raw, date):
            return raw
        return date.fromisoformat(str(raw))

    def _normalize_price_row(self, asset_id: str, row: dict, default_source: str) -> dict:
        day = self._parse_day(row.get("day"))
        close = float(row.get("close", 0))
        if close <= 0:
            raise ValidationError(f"provider returned non-positive close: {asset_id} {day.isoformat()}")
        source = str(row.get("source") or default_source).strip() or default_source
        return {"asset_id": asset_id.upper(), "day": day, "close": close, "source": source}

    def _normalize_fx_row(self, pair: str, row: dict, default_source: str) -> dict:
        normalized_pair = pair.upper()
        if "/" not in normalized_pair:
            raise ValidationError(f"invalid fx pair: {normalized_pair}")
        day = self._parse_day(row.get("day"))
        rate = float(row.get("rate", 0))
        if rate <= 0:
            raise ValidationError(f"provider returned non-positive fx rate: {normalized_pair} {day.isoformat()}")
        source = str(row.get("source") or default_source).strip() or default_source
        return {"pair": normalized_pair, "day": day, "rate": rate, "source": source}

    def fetch_prices(self, start_date: date, end_date: date, asset_ids: list[str]) -> list[dict]:
        rows: list[dict] = []
        for asset in asset_ids:
            asset_id = asset.upper()
            market = self.asset_market_map.get(asset_id)
            if not market:
                raise ValidationError(f"asset market mapping not found: {asset_id}")
            provider = self.providers_by_market.get(market)
            if not provider:
                raise ValidationError(f"provider not configured for market: {market}")
            symbol = self.asset_symbol_map.get(asset_id, asset_id)
            fetched = provider.fetch_price_rows(start_date, end_date, symbol)
            for row in fetched:
                rows.append(self._normalize_price_row(asset_id, row, default_source=provider.name))
        return rows

    def fetch_fx(self, start_date: date, end_date: date, pairs: list[str]) -> list[dict]:
        rows: list[dict] = []
        for raw_pair in pairs:
            pair = raw_pair.upper()
            fetched = self.fx_provider.fetch_fx_rows(start_date, end_date, pair)
            for row in fetched:
                rows.append(self._normalize_fx_row(pair, row, default_source=self.fx_provider.name))
        return rows


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


try:
    import akshare as ak
except ImportError:  # allow import without akshare installed (e.g. offline test envs)
    ak = None  # type: ignore[assignment]


@contextlib.contextmanager
def _no_proxy():
    """Temporarily remove proxy env vars so AKShare connects directly."""
    keys = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy")
    saved = {k: os.environ.pop(k) for k in keys if k in os.environ}
    try:
        yield
    finally:
        os.environ.update(saved)


def _akshare_fmt_date(d: date) -> str:
    return d.strftime("%Y%m%d")


class AKSharePriceProvider:
    """AKShare-backed price provider. One instance per market."""

    name = "akshare"

    def __init__(self, market: str) -> None:
        """market: 'cn' | 'us' | 'hk' | 'crypto' (case-insensitive)"""
        self.market = market.lower()

    @staticmethod
    def _is_etf(symbol: str) -> bool:
        # Shanghai ETFs: 51xxxx; Shenzhen ETFs: 159xxx.
        # A-share stocks use 0/3/6 prefix — no false positives in practice.
        s = symbol.upper()
        return s.startswith("5") or s.startswith("159")

    @staticmethod
    def _sina_prefix(symbol: str) -> str:
        """Return Sina-style prefix: sh/sz based on symbol."""
        if symbol.startswith("6") or symbol.startswith("5"):
            return f"sh{symbol}"
        return f"sz{symbol}"

    def _fetch_cn(self, start: str, end: str, symbol: str):
        """Fetch CN price data; try Sina first, fall back to eastmoney."""
        if self._is_etf(symbol):
            try:
                df = ak.fund_etf_hist_sina(symbol=self._sina_prefix(symbol))
                df["date"] = df["date"].astype(str)
                df = df[(df["date"] >= f"{start[:4]}-{start[4:6]}-{start[6:]}") &
                        (df["date"] <= f"{end[:4]}-{end[4:6]}-{end[6:]}")]
                return df, "date", "close"
            except Exception:
                pass
            df = ak.fund_etf_hist_em(
                symbol=symbol, period="daily", start_date=start, end_date=end, adjust="qfq"
            )
            return df, "日期", "收盘"
        else:
            try:
                df = ak.stock_zh_a_daily(
                    symbol=self._sina_prefix(symbol), start_date=start, end_date=end, adjust="qfq"
                )
                return df, "date", "close"
            except Exception:
                pass
            df = ak.stock_zh_a_hist(
                symbol=symbol, period="daily", start_date=start, end_date=end, adjust="qfq"
            )
            return df, "日期", "收盘"

    def fetch_price_rows(self, start_date: date, end_date: date, symbol: str) -> list[dict]:
        if ak is None:
            raise ImportError("akshare is not installed")
        start = _akshare_fmt_date(start_date)
        end = _akshare_fmt_date(end_date)
        with _no_proxy():
            if self.market == "cn":
                df, date_col, close_col = self._fetch_cn(start, end, symbol)
            elif self.market == "us":
                df = ak.stock_us_hist(
                    symbol=symbol, period="daily", start_date=start, end_date=end, adjust="qfq"
                )
                date_col, close_col = "日期", "收盘"
            elif self.market == "hk":
                df = ak.stock_hk_hist(
                    symbol=symbol, period="daily", start_date=start, end_date=end, adjust="qfq"
                )
                date_col, close_col = "日期", "收盘"
            elif self.market == "crypto":
                raise ValidationError("crypto market should use BinancePriceProvider, not AKSharePriceProvider")
            else:
                raise ValidationError(f"unsupported market for AKSharePriceProvider: {self.market}")

        rows: list[dict] = []
        for _, row in df.iterrows():
            rows.append({
                "day": date.fromisoformat(str(row[date_col])[:10]),
                "close": float(row[close_col]),
                "source": "akshare",
            })
        return rows


class AKShareFXProvider:
    """AKShare-backed FX provider."""

    name = "akshare"

    _PAIR_TO_SYMBOL = {
        "USD/CNY": "美元",
        "HKD/CNY": "港币",
    }

    def fetch_fx_rows(self, start_date: date, end_date: date, pair: str) -> list[dict]:
        if ak is None:
            raise ImportError("akshare is not installed")
        normalized = pair.upper()
        symbol = self._PAIR_TO_SYMBOL.get(normalized)
        if not symbol:
            raise ValidationError(f"unsupported FX pair for AKShareFXProvider: {pair}")
        start = _akshare_fmt_date(start_date)
        end = _akshare_fmt_date(end_date)
        with _no_proxy():
            df = ak.currency_boc_sina(symbol=symbol, start_date=start, end_date=end)
        rows: list[dict] = []
        for _, row in df.iterrows():
            # 中行折算价 is in "分" (e.g. 729.21 = 7.2921 CNY per USD)
            rate_raw = row.get("央行中间价")
            if rate_raw is None or (isinstance(rate_raw, float) and rate_raw != rate_raw):
                rate_raw = row.get("中行折算价")
            rows.append({
                "day": date.fromisoformat(str(row["日期"])[:10]),
                "rate": float(rate_raw) / 100.0,
                "source": "akshare",
            })
        return rows
