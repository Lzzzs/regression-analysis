"""Job request/response schemas shared by API and worker."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class ContractError(ValueError):
    """Raised when payload does not satisfy shared contract."""


@dataclass(slots=True)
class JobCreateRequest:
    weights: dict[str, float]
    snapshot_id: str
    start_date: str
    end_date: str
    rebalance_frequency: str
    base_currency: str = "CNY"
    max_retries: int | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "JobCreateRequest":
        try:
            req = cls(
                weights={str(k).upper(): float(v) for k, v in payload["weights"].items()},
                snapshot_id=str(payload["snapshot_id"]),
                start_date=str(payload["start_date"]),
                end_date=str(payload["end_date"]),
                rebalance_frequency=str(payload["rebalance_frequency"]).lower(),
                base_currency=str(payload.get("base_currency", "CNY")).upper(),
                max_retries=int(payload["max_retries"]) if "max_retries" in payload else None,
            )
        except Exception as exc:
            raise ContractError(f"请求参数无效: {exc}") from exc
        req.validate()
        return req

    def validate(self) -> None:
        if not self.snapshot_id:
            raise ContractError("缺少 snapshot_id")
        if not self.weights:
            raise ContractError("权重不能为空")
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ContractError(f"权重合计必须为 1.0，当前为 {total}")
        if self.rebalance_frequency not in {"none", "monthly", "quarterly"}:
            raise ContractError("再平衡频率必须为 none/monthly/quarterly")
        if self.max_retries is not None and self.max_retries < 0:
            raise ContractError("最大重试次数不能为负数")


@dataclass(slots=True)
class JobRecord:
    job_id: str
    payload: dict[str, Any]
    status: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    run_id: str | None = None
    retry_count: int = 0
    max_retries: int = 1
    last_error: str | None = None
    dead_lettered_at: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def new(cls, payload: dict[str, Any], max_retries: int = 1) -> "JobRecord":
        created_at = datetime.now(timezone.utc).isoformat()
        return cls(
            job_id=f"job-{uuid4().hex[:12]}",
            payload=payload,
            status="queued",
            created_at=created_at,
            max_retries=max_retries,
            events=[{"type": "created", "at": created_at}],
        )


@dataclass(slots=True)
class JobStatusResponse:
    job_id: str
    status: str
    created_at: str
    started_at: str | None
    finished_at: str | None
    error: str | None
    retry_count: int
    max_retries: int
    remaining_retries: int
    dead_lettered_at: str | None
    payload_summary: dict[str, Any]
    events: list[dict[str, Any]]


@dataclass(slots=True)
class JobResultResponse:
    job_id: str
    run_id: str
    snapshot_id: str
    metrics: dict[str, float]
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
