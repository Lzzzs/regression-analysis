"""Service layer for API job orchestration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from apps.shared.contracts import ContractError, JobCreateRequest, JobResultResponse, JobStatusResponse

from .job_store import JobStore


class JobService:
    def __init__(self, store: JobStore) -> None:
        self.store = store

    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = JobCreateRequest.from_payload(payload)
        job_data: dict[str, Any] = {
            "weights": request.weights,
            "snapshot_id": request.snapshot_id,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "rebalance_frequency": request.rebalance_frequency,
            "base_currency": request.base_currency,
            "max_retries": request.max_retries if request.max_retries is not None else self.store.max_retries,
        }
        if payload.get("assets"):
            job_data["assets"] = payload["assets"]
        record = self.store.create(job_data)
        return {"job_id": record.job_id, "status": record.status}

    @staticmethod
    def _payload_summary(payload: dict[str, Any]) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "snapshot_id": payload.get("snapshot_id"),
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
            "rebalance_frequency": payload.get("rebalance_frequency"),
            "base_currency": payload.get("base_currency"),
            "weights": payload.get("weights", {}),
        }
        if payload.get("assets"):
            summary["assets"] = payload["assets"]
        return summary

    def job_status(self, job_id: str) -> dict[str, Any]:
        item = self.store.get(job_id)
        retry_count = int(item.get("retry_count", 0))
        max_retries = int(item.get("max_retries", self.store.max_retries))
        response = JobStatusResponse(
            job_id=item["job_id"],
            status=item["status"],
            created_at=item["created_at"],
            started_at=item.get("started_at"),
            finished_at=item.get("finished_at"),
            error=item.get("error"),
            retry_count=retry_count,
            max_retries=max_retries,
            remaining_retries=max(0, max_retries - retry_count),
            dead_lettered_at=item.get("dead_lettered_at"),
            payload_summary=self._payload_summary(item.get("payload", {})),
            events=list(item.get("events", [])),
        )
        return asdict(response)

    def job_result(self, job_id: str) -> dict[str, Any]:
        item = self.store.get(job_id)
        if item["status"] != "completed":
            raise ContractError("任务尚未完成")
        result = self.store.get_result(job_id)
        response = JobResultResponse(
            job_id=job_id,
            run_id=result["run_id"],
            snapshot_id=result["snapshot_id"],
            metrics=result["metrics"],
            equity_curve=result["equity_curve"],
            yearly_returns=result.get("yearly_returns", []),
            monthly_returns=result.get("monthly_returns", []),
            top_drawdowns=result.get("top_drawdowns", []),
        )
        return asdict(response)

    @staticmethod
    def _with_retry_hints(item: dict[str, Any], default_max: int) -> dict[str, Any]:
        retry_count = int(item.get("retry_count", 0))
        max_retries = int(item.get("max_retries", default_max))
        enriched = dict(item)
        enriched["retry_count"] = retry_count
        enriched["max_retries"] = max_retries
        enriched["remaining_retries"] = max(0, max_retries - retry_count)
        return enriched

    def list_jobs(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
        q: str | None = None,
    ) -> dict[str, Any]:
        data = self.store.list_jobs(status=status, limit=limit, offset=offset, q=q)
        items = [self._with_retry_hints(item, self.store.max_retries) for item in data["items"]]
        return {
            "items": items,
            "count": len(items),
            "total": data["total"],
            "offset": data["offset"],
            "limit": data["limit"],
        }

    def dead_letter_jobs(self, limit: int = 100, offset: int = 0, q: str | None = None) -> dict[str, Any]:
        return self.list_jobs(status="dead-letter", limit=limit, offset=offset, q=q)

    def requeue_job(self, job_id: str) -> dict[str, Any]:
        try:
            item = self.store.requeue(job_id)
        except ValueError as exc:
            raise ContractError(str(exc)) from exc
        retry_count = int(item.get("retry_count", 0))
        max_retries = int(item.get("max_retries", self.store.max_retries))
        return {
            "job_id": item["job_id"],
            "status": item["status"],
            "retry_count": retry_count,
            "max_retries": max_retries,
            "remaining_retries": max(0, max_retries - retry_count),
        }
