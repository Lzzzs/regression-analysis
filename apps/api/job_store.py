"""Job repository with pluggable queue backends."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from apps.shared.contracts import JobRecord

from .queue_backends import FileQueueBackend, QueueBackend, RedisQueueBackend, build_redis_client


class JobStore:
    def __init__(
        self,
        base_dir: str | Path = "data",
        backend: str | None = None,
        redis_url: str | None = None,
        redis_client: Any | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.backend_name = (backend or os.getenv("JOB_QUEUE_BACKEND", "file")).strip().lower()
        self.max_retries = max_retries if max_retries is not None else int(os.getenv("JOB_MAX_RETRIES", "1"))

        if self.backend_name == "redis":
            if redis_client is None:
                client = build_redis_client(redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0"))
            else:
                client = redis_client
            self.backend: QueueBackend = RedisQueueBackend(client, max_retries=self.max_retries)
        else:
            self.backend = FileQueueBackend(self.base_dir, max_retries=self.max_retries)

    def create(self, payload: dict[str, Any]) -> JobRecord:
        max_retries = int(payload.get("max_retries", self.max_retries))
        record = JobRecord.new(payload, max_retries=max_retries)
        self.backend.create(self._to_payload(record))
        return record

    def get(self, job_id: str) -> dict[str, Any]:
        return self.backend.get(job_id)

    def update(self, job_id: str, **patch: Any) -> dict[str, Any]:
        return self.backend.update(job_id, **patch)

    def list_by_status(self, status: str) -> list[dict[str, Any]]:
        return self.backend.list_by_status(status)

    def list_jobs(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
        q: str | None = None,
    ) -> dict[str, Any]:
        items = self.backend.list_by_status(status) if status else self.backend.list_all()
        if q:
            needle = q.strip().lower()
            items = [
                item
                for item in items
                if needle in str(item.get("job_id", "")).lower()
                or needle in str(item.get("status", "")).lower()
                or needle in str(item.get("payload", {}).get("snapshot_id", "")).lower()
            ]
        total = len(items)
        start = max(0, offset)
        end = start + max(0, limit)
        return {
            "items": items[start:end],
            "total": total,
            "offset": start,
            "limit": max(0, limit),
        }

    def requeue(self, job_id: str) -> dict[str, Any]:
        return self.backend.requeue(job_id)

    def claim_next_queued(self) -> dict[str, Any] | None:
        return self.backend.claim_next_queued()

    def mark_completed(self, job_id: str, run_id: str) -> dict[str, Any]:
        return self.backend.mark_completed(job_id, run_id)

    def mark_failed(self, job_id: str, error: str) -> dict[str, Any]:
        return self.backend.mark_failed(job_id, error)

    def save_result(self, job_id: str, payload: dict[str, Any]) -> None:
        self.backend.save_result(job_id, payload)

    def get_result(self, job_id: str) -> dict[str, Any]:
        return self.backend.get_result(job_id)

    @staticmethod
    def _to_payload(record: JobRecord) -> dict[str, Any]:
        return {
            "job_id": record.job_id,
            "payload": record.payload,
            "status": record.status,
            "created_at": record.created_at,
            "started_at": record.started_at,
            "finished_at": record.finished_at,
            "error": record.error,
            "run_id": record.run_id,
            "retry_count": record.retry_count,
            "max_retries": record.max_retries,
            "last_error": record.last_error,
            "dead_lettered_at": record.dead_lettered_at,
            "events": list(record.events),
        }
