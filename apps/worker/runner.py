"""Background worker that consumes queued jobs and executes backtests."""

from __future__ import annotations

import time
from pathlib import Path

from apps.api.job_store import JobStore
from portfolio_lab.backtest import BacktestEngine
from apps.shared.execution import execute_backtest_job


class BacktestWorker:
    def __init__(self, data_dir: str | Path = "data", store: JobStore | None = None) -> None:
        self.data_dir = Path(data_dir)
        self.store = store or JobStore(self.data_dir)
        self.engine = BacktestEngine(self.data_dir)

    def run_once(self) -> bool:
        job = self.store.claim_next_queued()
        if not job:
            return False

        execute_backtest_job(
            job_id=job["job_id"],
            payload=job["payload"],
            engine=self.engine,
            save_result=self.store.save_result,
            mark_completed=self.store.mark_completed,
            mark_failed=self.store.mark_failed,
            update_job=self.store.update,
        )
        return True

    def run_forever(self, poll_seconds: float = 1.0) -> None:
        while True:
            processed = self.run_once()
            if not processed:
                time.sleep(poll_seconds)


if __name__ == "__main__":
    worker = BacktestWorker()
    worker.run_forever()
