"""Snapshot creation service powered by provider-based adapters."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

from portfolio_lab.data_adapters import LocalCSVFXProvider, LocalCSVPriceProvider, RoutedMarketDataAdapter
from portfolio_lab.errors import SnapshotError, ValidationError
from portfolio_lab.models import AssetDefinition, AssetType, CalendarType
from portfolio_lab.universe import UniverseStore

ASSET_CATALOG: dict[str, dict[str, Any]] = {
    "CSI300": {
        "identifier": "CSI300",
        "asset_type": AssetType.INDEX,
        "market": "CN",
        "calendar": CalendarType.A_SHARE,
        "quote_currency": "CNY",
    },
    "SPY": {
        "identifier": "SPY",
        "asset_type": AssetType.ETF,
        "market": "US",
        "calendar": CalendarType.US_EQUITY,
        "quote_currency": "USD",
    },
    "BTC": {
        "identifier": "BTC",
        "asset_type": AssetType.CRYPTO,
        "market": "CRYPTO",
        "calendar": CalendarType.CRYPTO_7D,
        "quote_currency": "USD",
    },
}

DEFAULT_SYMBOL_MAP = {
    "CSI300": "000300.SH",
    "SPY": "SPY",
    "BTC": "BTCUSDT",
}

DEFAULT_PROVIDER_FILES = {
    "cn_prices": "data/providers/cn_prices.csv",
    "us_prices": "data/providers/us_prices.csv",
    "crypto_prices": "data/providers/crypto_prices.csv",
    "fx_rates": "data/providers/fx_rates.csv",
}


class SnapshotService:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)

    @staticmethod
    def _to_date(value: Any, field_name: str) -> date:
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except Exception as exc:
            raise ValidationError(f"{field_name} must be YYYY-MM-DD") from exc

    @staticmethod
    def _to_upper_list(value: Any, field_name: str) -> list[str]:
        if not isinstance(value, list) or not value:
            raise ValidationError(f"{field_name} must be a non-empty list")
        items = [str(item).upper().strip() for item in value]
        if any(not item for item in items):
            raise ValidationError(f"{field_name} cannot contain empty values")
        return items

    @staticmethod
    def _resolve_file(path_value: Any, default_rel_path: str) -> Path:
        raw = str(path_value).strip() if path_value is not None else default_rel_path
        path = Path(raw)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            raise ValidationError(f"provider file not found: {path}")
        return path

    def _build_store(self, selected_assets: list[str]) -> UniverseStore:
        store = UniverseStore(self.data_dir)
        for asset_id in selected_assets:
            config = ASSET_CATALOG.get(asset_id)
            if not config:
                raise ValidationError(f"asset not supported by provider snapshot service: {asset_id}")
            store.register_asset(AssetDefinition(**deepcopy(config)))
        return store

    def create_snapshot_from_providers(self, payload: dict[str, Any]) -> dict[str, Any]:
        coverage_start = self._to_date(payload.get("coverage_start"), "coverage_start")
        week_end = self._to_date(payload.get("week_end"), "week_end")
        selected_assets = self._to_upper_list(payload.get("selected_assets"), "selected_assets")
        required_fx_pairs = self._to_upper_list(payload.get("required_fx_pairs"), "required_fx_pairs")
        if coverage_start > week_end:
            raise ValidationError("coverage_start must be <= week_end")

        provider_files = payload.get("provider_files", {}) or {}
        if not isinstance(provider_files, dict):
            raise ValidationError("provider_files must be an object")

        symbol_map_input = payload.get("asset_symbol_map", {}) or {}
        if not isinstance(symbol_map_input, dict):
            raise ValidationError("asset_symbol_map must be an object")
        symbol_map = {k.upper(): str(v).upper() for k, v in DEFAULT_SYMBOL_MAP.items()}
        symbol_map.update({str(k).upper(): str(v).upper() for k, v in symbol_map_input.items()})

        cn_prices_file = self._resolve_file(provider_files.get("cn_prices"), DEFAULT_PROVIDER_FILES["cn_prices"])
        us_prices_file = self._resolve_file(provider_files.get("us_prices"), DEFAULT_PROVIDER_FILES["us_prices"])
        crypto_prices_file = self._resolve_file(
            provider_files.get("crypto_prices"), DEFAULT_PROVIDER_FILES["crypto_prices"]
        )
        fx_rates_file = self._resolve_file(provider_files.get("fx_rates"), DEFAULT_PROVIDER_FILES["fx_rates"])

        providers_by_market = {
            "CN": LocalCSVPriceProvider(cn_prices_file, name="cn-csv"),
            "US": LocalCSVPriceProvider(us_prices_file, name="us-csv"),
            "CRYPTO": LocalCSVPriceProvider(crypto_prices_file, name="crypto-csv"),
        }
        fx_provider = LocalCSVFXProvider(fx_rates_file, name="fx-csv")

        asset_market_map: dict[str, str] = {}
        for asset_id in selected_assets:
            config = ASSET_CATALOG.get(asset_id)
            if not config:
                raise ValidationError(f"asset not supported by provider snapshot service: {asset_id}")
            asset_market_map[asset_id] = str(config["market"]).upper()

        adapter = RoutedMarketDataAdapter(
            providers_by_market=providers_by_market,
            fx_provider=fx_provider,
            asset_market_map=asset_market_map,
            asset_symbol_map=symbol_map,
        )

        store = self._build_store(selected_assets)
        store.ingest_from_adapter(adapter, coverage_start, week_end, selected_assets, required_fx_pairs)
        snapshot_id = store.publish_weekly_snapshot(
            week_end=week_end,
            selected_assets=selected_assets,
            required_fx_pairs=required_fx_pairs,
            coverage_start=coverage_start,
        )
        snapshot = store.load_snapshot(snapshot_id)
        return {
            "snapshot_id": snapshot_id,
            "coverage": snapshot["coverage"],
            "traceability": snapshot["traceability"],
            "integrity": snapshot["integrity"],
        }


def build_snapshot_service(data_dir: str | Path = "data") -> SnapshotService:
    return SnapshotService(data_dir=data_dir)
