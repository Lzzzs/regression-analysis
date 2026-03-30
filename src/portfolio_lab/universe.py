"""Universe registry, ingestion, and snapshot publishing."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from .data_adapters import MarketDataAdapter
from .errors import DuplicateAssetError, SnapshotError, ValidationError
from .models import AssetDefinition, CalendarType, FXPoint, PricePoint, to_primitive


def daterange(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def is_trading_day(day: date, calendar: CalendarType) -> bool:
    if calendar == CalendarType.CRYPTO_7D:
        return True
    return day.weekday() < 5


def expected_trading_days(start: date, end: date, calendar: CalendarType) -> list[date]:
    return [d for d in daterange(start, end) if is_trading_day(d, calendar)]


def snapshot_checksum(payload: dict) -> str:
    """Compute deterministic checksum from snapshot payload excluding integrity section."""

    checksum_payload = {k: v for k, v in payload.items() if k != "integrity"}
    canonical = json.dumps(checksum_payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_snapshot_integrity(payload: dict) -> None:
    integrity = payload.get("integrity")
    if not isinstance(integrity, dict):
        raise SnapshotError("snapshot integrity section is required")
    if integrity.get("algorithm") != "sha256":
        raise SnapshotError("snapshot integrity algorithm must be sha256")
    expected = integrity.get("checksum_sha256")
    if not isinstance(expected, str) or not expected:
        raise SnapshotError("snapshot checksum_sha256 is required")
    actual = snapshot_checksum(payload)
    if expected != actual:
        raise SnapshotError("snapshot integrity check failed")


class UniverseStore:
    """In-memory registry with snapshot persistence to local filesystem."""

    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.snapshot_dir = self.data_dir / "snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.assets: dict[str, AssetDefinition] = {}
        self.prices: dict[str, dict[date, PricePoint]] = defaultdict(dict)
        self.fx_rates: dict[str, dict[date, FXPoint]] = defaultdict(dict)
        self.ingestion_days: set[date] = set()

    def register_asset(self, asset: AssetDefinition) -> None:
        if asset.identifier in self.assets:
            raise DuplicateAssetError(f"asset already exists: {asset.identifier}")
        self.assets[asset.identifier] = asset

    def ingest_prices(self, rows: list[dict]) -> list[dict]:
        errors: list[dict] = []
        seen: dict[tuple[str, date], PricePoint] = {}
        for idx, row in enumerate(rows):
            try:
                point = PricePoint(
                    asset_id=str(row["asset_id"]).upper(),
                    day=row["day"] if isinstance(row["day"], date) else date.fromisoformat(str(row["day"])),
                    close=float(row["close"]),
                    source=str(row.get("source", "unknown")),
                )
                if point.asset_id not in self.assets:
                    raise ValidationError(f"unknown asset: {point.asset_id}")
                asset = self.assets[point.asset_id]
                if asset.calendar != CalendarType.CRYPTO_7D and point.day.weekday() >= 5:
                    raise ValidationError(
                        f"non-crypto asset on non-trading day: {point.asset_id} {point.day.isoformat()}"
                    )
                key = (point.asset_id, point.day)
                existing = seen.get(key)
                if existing and (existing.close != point.close or existing.source != point.source):
                    raise ValidationError(
                        f"conflicting duplicate price row: {point.asset_id} {point.day.isoformat()}"
                    )
                seen[key] = point
                self.prices[point.asset_id][point.day] = point
                self.ingestion_days.add(point.day)
            except Exception as exc:  # row-level validation
                errors.append({"row": idx, "error": str(exc), "payload": row})
        if errors:
            raise ValidationError(f"price ingestion failed: {errors}")
        return errors

    def ingest_fx(self, rows: list[dict]) -> list[dict]:
        errors: list[dict] = []
        seen: dict[tuple[str, date], FXPoint] = {}
        for idx, row in enumerate(rows):
            try:
                point = FXPoint(
                    pair=str(row["pair"]).upper(),
                    day=row["day"] if isinstance(row["day"], date) else date.fromisoformat(str(row["day"])),
                    rate=float(row["rate"]),
                    source=str(row.get("source", "unknown")),
                )
                key = (point.pair, point.day)
                existing = seen.get(key)
                if existing and (existing.rate != point.rate or existing.source != point.source):
                    raise ValidationError(f"conflicting duplicate fx row: {point.pair} {point.day.isoformat()}")
                seen[key] = point
                self.fx_rates[point.pair][point.day] = point
                self.ingestion_days.add(point.day)
            except Exception as exc:
                errors.append({"row": idx, "error": str(exc), "payload": row})
        if errors:
            raise ValidationError(f"fx ingestion failed: {errors}")
        return errors

    def ingest_daily_increment(self, day: date, price_rows: list[dict], fx_rows: list[dict]) -> None:
        for row in price_rows:
            row["day"] = day
        for row in fx_rows:
            row["day"] = day
        self.ingest_prices(price_rows)
        self.ingest_fx(fx_rows)

    def ingest_from_adapter(
        self,
        adapter: MarketDataAdapter,
        start_date: date,
        end_date: date,
        selected_assets: list[str],
        required_fx_pairs: list[str],
    ) -> None:
        prices = adapter.fetch_prices(start_date, end_date, [asset.upper() for asset in selected_assets])
        fx_rows = adapter.fetch_fx(start_date, end_date, [pair.upper() for pair in required_fx_pairs])
        self.ingest_prices(prices)
        self.ingest_fx(fx_rows)

    def query_assets(self, asset_ids: list[str]) -> list[dict]:
        result = []
        for raw_id in asset_ids:
            asset_id = raw_id.upper()
            asset = self.assets.get(asset_id)
            if not asset:
                raise ValidationError(f"asset not found: {asset_id}")
            result.append(
                {
                    "identifier": asset.identifier,
                    "calendar": asset.calendar.value,
                    "quote_currency": asset.quote_currency,
                    "market": asset.market,
                    "asset_type": asset.asset_type.value,
                    "tags": list(asset.tags),
                }
            )
        return result

    def _quality_gate(
        self,
        selected_assets: list[str],
        start_date: date,
        end_date: date,
        required_fx_pairs: list[str],
    ) -> None:
        missing: list[dict] = []
        for asset_id in selected_assets:
            asset = self.assets[asset_id]
            asset_prices = self.prices.get(asset_id, {})
            for day in expected_trading_days(start_date, end_date, asset.calendar):
                if day not in asset_prices:
                    missing.append({"type": "price", "asset_id": asset_id, "day": day.isoformat()})

        for pair in required_fx_pairs:
            pair = pair.upper()
            fx_series = self.fx_rates.get(pair, {})
            for day in daterange(start_date, end_date):
                if day.weekday() < 5 and day not in fx_series:
                    missing.append({"type": "fx", "pair": pair, "day": day.isoformat()})

        if missing:
            raise SnapshotError(f"snapshot quality gate failed: {missing}")

    def publish_weekly_snapshot(
        self,
        week_end: date,
        selected_assets: list[str],
        required_fx_pairs: list[str],
        coverage_start: date,
        skip_quality_gate: bool = False,
    ) -> str:
        if week_end.weekday() != 4:
            raise SnapshotError("weekly frozen snapshot must use Friday as week_end")

        normalized_assets = [a.upper() for a in selected_assets]
        for asset_id in normalized_assets:
            if asset_id not in self.assets:
                raise SnapshotError(f"unknown asset: {asset_id}")

        if not skip_quality_gate:
            self._quality_gate(normalized_assets, coverage_start, week_end, required_fx_pairs)

        snapshot_id = f"snap-{week_end.isoformat()}-{uuid4().hex[:8]}"
        out_file = self.snapshot_dir / f"{snapshot_id}.json"
        if out_file.exists():
            raise SnapshotError(f"snapshot already exists: {snapshot_id}")

        payload = {
            "snapshot_id": snapshot_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cadence": "daily_increment_weekly_frozen",
            "coverage": {
                "start_date": coverage_start.isoformat(),
                "end_date": week_end.isoformat(),
            },
            "assets": {
                aid: to_primitive(self.assets[aid])
                for aid in normalized_assets
            },
            "prices": {
                aid: {
                    d.isoformat(): to_primitive(p)
                    for d, p in sorted(self.prices[aid].items(), key=lambda item: item[0])
                    if coverage_start <= d <= week_end
                }
                for aid in normalized_assets
            },
            "fx": {
                pair.upper(): {
                    d.isoformat(): to_primitive(point)
                    for d, point in sorted(self.fx_rates[pair.upper()].items(), key=lambda item: item[0])
                    if coverage_start <= d <= week_end
                }
                for pair in required_fx_pairs
            },
            "traceability": {
                "sources": sorted(
                    {
                        p.source
                        for aid in normalized_assets
                        for p in self.prices[aid].values()
                        if coverage_start <= p.day <= week_end
                    }
                    | {
                        x.source
                        for pair in required_fx_pairs
                        for x in self.fx_rates[pair.upper()].values()
                        if coverage_start <= x.day <= week_end
                    }
                )
            },
        }
        payload["integrity"] = {
            "algorithm": "sha256",
            "checksum_sha256": snapshot_checksum(payload),
        }

        out_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return snapshot_id

    def load_snapshot(self, snapshot_id: str) -> dict:
        file_path = self.snapshot_dir / f"{snapshot_id}.json"
        if not file_path.exists():
            raise SnapshotError(f"snapshot not found: {snapshot_id}")
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        verify_snapshot_integrity(payload)
        return payload
