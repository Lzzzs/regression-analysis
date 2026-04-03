"""Queue backend abstractions and implementations (file + redis)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QueueBackend(ABC):
    def __init__(self, max_retries: int = 1) -> None:
        self.max_retries = max_retries

    @abstractmethod
    def create(self, record: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, job_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update(self, job_id: str, **patch: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_by_status(self, status: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def claim_next_queued(self) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def save_result(self, job_id: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_result(self, job_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def mark_completed(self, job_id: str, run_id: str) -> dict[str, Any]:
        item = self.get(job_id)
        finished_at = utc_now()
        return self.update(
            job_id,
            status="completed",
            run_id=run_id,
            finished_at=finished_at,
            error=None,
            events=self._append_event(item, "completed", finished_at, run_id=run_id),
        )

    def mark_failed(self, job_id: str, error: str) -> dict[str, Any]:
        item = self.get(job_id)
        retry_count = int(item.get("retry_count", 0))
        max_retries = int(item.get("max_retries", self.max_retries))
        failed_at = utc_now()
        failed_events = self._append_event(item, "failed", failed_at, error=error)

        if retry_count < max_retries:
            retry_count += 1
            retry_events = self._append_event(
                {**item, "events": failed_events},
                "retry_scheduled",
                failed_at,
                retry_count=retry_count,
                max_retries=max_retries,
            )
            updated = self.update(
                job_id,
                status="queued",
                error=error,
                retry_count=retry_count,
                last_error=error,
                finished_at=None,
                events=retry_events,
            )
            self._enqueue(job_id)
            return updated

        return self._mark_dead_letter(
            job_id,
            error,
            item={**item, "events": failed_events},
            timestamp=failed_at,
        )

    @abstractmethod
    def _enqueue(self, job_id: str) -> None:
        raise NotImplementedError

    def requeue(self, job_id: str) -> dict[str, Any]:
        item = self.get(job_id)
        if item.get("status") not in {"dead-letter", "failed"}:
            raise ValueError("only dead-letter/failed jobs can be requeued")
        requeue_at = utc_now()
        updated = self.update(
            job_id,
            status="queued",
            started_at=None,
            finished_at=None,
            error=None,
            dead_lettered_at=None,
            retry_count=0,
            events=self._append_event(item, "requeued", requeue_at),
        )
        self._enqueue(job_id)
        return updated

    @staticmethod
    def _append_event(
        item: dict[str, Any],
        event_type: str,
        timestamp: str | None = None,
        **extra: Any,
    ) -> list[dict[str, Any]]:
        events = list(item.get("events", []))
        event: dict[str, Any] = {"type": event_type, "at": timestamp or utc_now()}
        for key, value in extra.items():
            if value is not None:
                event[key] = value
        events.append(event)
        return events

    def _mark_dead_letter(
        self,
        job_id: str,
        error: str,
        item: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        dead_lettered_at = timestamp or utc_now()
        current = item or self.get(job_id)
        return self.update(
            job_id,
            status="dead-letter",
            error=error,
            dead_lettered_at=dead_lettered_at,
            finished_at=dead_lettered_at,
            events=self._append_event(current, "dead_lettered", dead_lettered_at, error=error),
        )


class FileQueueBackend(QueueBackend):
    def __init__(self, base_dir: str | Path = "data", max_retries: int = 1) -> None:
        super().__init__(max_retries=max_retries)
        self.base_dir = Path(base_dir)
        self.jobs_dir = self.base_dir / "jobs"
        self.results_dir = self.base_dir / "job_results"
        self.dead_dir = self.base_dir / "jobs_dead"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.dead_dir.mkdir(parents=True, exist_ok=True)

    def create(self, record: dict[str, Any]) -> None:
        self._write_json(self.jobs_dir / f"{record['job_id']}.json", record)

    def get(self, job_id: str) -> dict[str, Any]:
        file_path = self.jobs_dir / f"{job_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"job not found: {job_id}")
        return json.loads(file_path.read_text(encoding="utf-8"))

    def update(self, job_id: str, **patch: Any) -> dict[str, Any]:
        data = self.get(job_id)
        data.update(patch)
        self._write_json(self.jobs_dir / f"{job_id}.json", data)
        return data

    def list_by_status(self, status: str) -> list[dict[str, Any]]:
        records = []
        for file_path in sorted(self.jobs_dir.glob("*.json")):
            data = json.loads(file_path.read_text(encoding="utf-8"))
            if data.get("status") == status:
                records.append(data)
        return records

    def list_all(self) -> list[dict[str, Any]]:
        records = []
        for file_path in sorted(self.jobs_dir.glob("*.json")):
            records.append(json.loads(file_path.read_text(encoding="utf-8")))
        records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return records

    def claim_next_queued(self) -> dict[str, Any] | None:
        queued = self.list_by_status("queued")
        if not queued:
            return None
        record = queued[0]
        started_at = utc_now()
        record["status"] = "running"
        record["started_at"] = started_at
        record["events"] = self._append_event(record, "started", started_at)
        self._write_json(self.jobs_dir / f"{record['job_id']}.json", record)
        return record

    def save_result(self, job_id: str, payload: dict[str, Any]) -> None:
        self._write_json(self.results_dir / f"{job_id}.json", payload)

    def get_result(self, job_id: str) -> dict[str, Any]:
        file_path = self.results_dir / f"{job_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"job result not found: {job_id}")
        return json.loads(file_path.read_text(encoding="utf-8"))

    def _enqueue(self, job_id: str) -> None:
        # File backend uses status scan; no explicit queue structure needed.
        _ = job_id

    def _mark_dead_letter(
        self,
        job_id: str,
        error: str,
        item: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        updated = super()._mark_dead_letter(job_id, error, item=item, timestamp=timestamp)
        self._write_json(self.dead_dir / f"{job_id}.json", updated)
        return updated

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


class RedisQueueBackend(QueueBackend):
    QUEUED_KEY = "jobs:queued"
    DEAD_KEY = "jobs:dead"

    def __init__(self, redis_client: Any, max_retries: int = 1) -> None:
        super().__init__(max_retries=max_retries)
        self.client = redis_client

    @staticmethod
    def _job_key(job_id: str) -> str:
        return f"jobs:data:{job_id}"

    @staticmethod
    def _result_key(job_id: str) -> str:
        return f"jobs:result:{job_id}"

    def create(self, record: dict[str, Any]) -> None:
        job_id = record["job_id"]
        self.client.set(self._job_key(job_id), json.dumps(record, ensure_ascii=True))
        self.client.rpush(self.QUEUED_KEY, job_id)

    def get(self, job_id: str) -> dict[str, Any]:
        raw = self.client.get(self._job_key(job_id))
        if raw is None:
            raise FileNotFoundError(f"job not found: {job_id}")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def update(self, job_id: str, **patch: Any) -> dict[str, Any]:
        data = self.get(job_id)
        data.update(patch)
        self.client.set(self._job_key(job_id), json.dumps(data, ensure_ascii=True))
        return data

    def list_by_status(self, status: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for item in self.list_all():
            if item.get("status") == status:
                records.append(item)
        return records

    def list_all(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for key in self.client.keys("jobs:data:*"):
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            raw = self.client.get(key)
            if raw is None:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            records.append(json.loads(raw))
        records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return records

    def claim_next_queued(self) -> dict[str, Any] | None:
        job_id = self.client.lpop(self.QUEUED_KEY)
        if not job_id:
            return None
        if isinstance(job_id, bytes):
            job_id = job_id.decode("utf-8")
        item = self.get(job_id)
        started_at = utc_now()
        return self.update(
            job_id,
            status="running",
            started_at=started_at,
            events=self._append_event(item, "started", started_at),
        )

    def save_result(self, job_id: str, payload: dict[str, Any]) -> None:
        self.client.set(self._result_key(job_id), json.dumps(payload, ensure_ascii=True))

    def get_result(self, job_id: str) -> dict[str, Any]:
        raw = self.client.get(self._result_key(job_id))
        if raw is None:
            raise FileNotFoundError(f"job result not found: {job_id}")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def _enqueue(self, job_id: str) -> None:
        self.client.rpush(self.QUEUED_KEY, job_id)

    def _mark_dead_letter(
        self,
        job_id: str,
        error: str,
        item: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        updated = super()._mark_dead_letter(job_id, error, item=item, timestamp=timestamp)
        self.client.rpush(self.DEAD_KEY, job_id)
        return updated


def build_redis_client(redis_url: str):
    try:
        import redis  # type: ignore
    except Exception as exc:
        raise RuntimeError("redis package is required for JOB_QUEUE_BACKEND=redis") from exc
    return redis.Redis.from_url(redis_url)
