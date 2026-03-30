"""Higher-level API orchestration for one-click analysis flows."""

from __future__ import annotations

from datetime import date
from typing import Any

from apps.shared.contracts import ContractError, JobCreateRequest
from portfolio_lab.errors import SnapshotError, ValidationError

from .asset_router import resolve_asset_meta
from .snapshot_service import ASSET_CATALOG, SnapshotService
from .service import JobService


class AutoJobOrchestrator:
    """Create snapshot from providers and queue a backtest job in one request."""

    def __init__(self, job_service: JobService, snapshot_service: SnapshotService) -> None:
        self.job_service = job_service
        self.snapshot_service = snapshot_service

    @staticmethod
    def _infer_fx_pairs(selected_assets: list[str], base_currency: str) -> list[str]:
        """Infer FX pairs from ASSET_CATALOG (backward-compat CSV path)."""
        pairs: set[str] = set()
        for asset_id in selected_assets:
            catalog = ASSET_CATALOG.get(asset_id)
            if not catalog:
                continue
            quote = str(catalog["quote_currency"]).upper()
            if quote != base_currency:
                pairs.add(f"{quote}/{base_currency}")
        return sorted(pairs)

    @staticmethod
    def _infer_fx_pairs_from_assets(assets: list[dict], base_currency: str) -> list[str]:
        """Infer FX pairs from assets metadata (AKShare path)."""
        pairs: set[str] = set()
        for a in assets:
            meta = resolve_asset_meta(str(a["code"]), str(a["market"]))
            quote = meta["quote_currency"].upper()
            if quote != base_currency:
                pairs.add(f"{quote}/{base_currency}")
        return sorted(pairs)

    def create_job_auto(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized_for_validation = {
            "weights": payload.get("weights"),
            "snapshot_id": "AUTO-SNAPSHOT",
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
            "rebalance_frequency": payload.get("rebalance_frequency"),
            "base_currency": payload.get("base_currency", "CNY"),
        }
        if payload.get("max_retries") is not None:
            normalized_for_validation["max_retries"] = payload.get("max_retries")
        request = JobCreateRequest.from_payload(normalized_for_validation)

        start_date = date.fromisoformat(request.start_date)
        end_date = date.fromisoformat(request.end_date)
        if end_date.weekday() != 4:
            raise ContractError("结束日期必须为周五（快照按周发布）")
        if start_date > end_date:
            raise ContractError("开始日期不能晚于结束日期")

        selected_assets_raw = payload.get("selected_assets")
        if selected_assets_raw is None:
            selected_assets = sorted(request.weights.keys())
        elif isinstance(selected_assets_raw, list) and selected_assets_raw:
            selected_assets = sorted({str(item).upper() for item in selected_assets_raw})
        else:
            raise ContractError("selected_assets 不能为空列表")

        missing_weight_assets = [asset for asset in request.weights if asset not in selected_assets]
        if missing_weight_assets:
            raise ContractError(f"权重中包含未选中的资产: {missing_weight_assets}")

        assets_raw = payload.get("assets")  # list[{code, market, asset_type}] | None
        required_fx_raw = payload.get("required_fx_pairs")

        if required_fx_raw is None:
            if assets_raw:
                required_fx_pairs = self._infer_fx_pairs_from_assets(assets_raw, request.base_currency)
            else:
                required_fx_pairs = self._infer_fx_pairs(selected_assets, request.base_currency)
        elif isinstance(required_fx_raw, list):
            required_fx_pairs = sorted({str(item).upper() for item in required_fx_raw})
        else:
            raise ContractError("required_fx_pairs 必须为列表格式")

        snapshot_payload: dict[str, Any] = {
            "coverage_start": request.start_date,
            "week_end": request.end_date,
            "selected_assets": selected_assets,
            "required_fx_pairs": required_fx_pairs if required_fx_pairs else ["USD/CNY"],
            "provider_files": payload.get("provider_files", {}) or {},
            "asset_symbol_map": payload.get("asset_symbol_map", {}) or {},
        }
        if assets_raw:
            snapshot_payload["assets"] = assets_raw

        snapshot = self.snapshot_service.create_snapshot_from_providers(snapshot_payload)

        job_payload = {
            "weights": request.weights,
            "snapshot_id": snapshot["snapshot_id"],
            "start_date": request.start_date,
            "end_date": request.end_date,
            "rebalance_frequency": request.rebalance_frequency,
            "base_currency": request.base_currency,
        }
        if request.max_retries is not None:
            job_payload["max_retries"] = request.max_retries
        created = self.job_service.create_job(job_payload)
        return {
            "job_id": created["job_id"],
            "status": created["status"],
            "snapshot_id": snapshot["snapshot_id"],
            "snapshot": snapshot,
        }


def map_auto_job_error(exc: Exception) -> ContractError:
    if isinstance(exc, ContractError):
        return exc
    if isinstance(exc, (ValidationError, SnapshotError, FileNotFoundError)):
        return ContractError(str(exc))
    return ContractError(f"一键分析失败: {exc}")
