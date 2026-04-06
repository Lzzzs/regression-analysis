"""Inline worker that processes a single job synchronously within the API request."""

from __future__ import annotations

from portfolio_lab.backtest import BacktestEngine

from .job_store import JobStore
from .queue_backends import utc_now
from apps.shared.execution import execute_backtest_job


class InlineWorker:
    """Run a backtest job synchronously. Used by /jobs/auto to return results immediately."""

    def __init__(self, store: JobStore) -> None:
        self.store = store
        self.engine = BacktestEngine(store.base_dir)

    def process_job(self, job_id: str) -> None:
        try:
            job = self.store.get(job_id)
        except FileNotFoundError:
            return
        if job.get("status") != "queued":
            return
        # Directly transition this specific job to running
        self.store.update(job_id, status="running", started_at=utc_now())

        execute_backtest_job(
            job_id=job_id,
            payload=job["payload"],
            engine=self.engine,
            save_result=self.store.save_result,
            mark_completed=self.store.mark_completed,
            mark_failed=self.store.mark_failed,
            update_job=self.store.update,
        )
