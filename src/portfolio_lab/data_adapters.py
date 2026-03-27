"""Market data adapter abstractions and offline implementations."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Protocol

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
