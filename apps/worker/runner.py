"""Background worker that consumes queued jobs and executes backtests."""

from __future__ import annotations

import time
from datetime import date
from pathlib import Path

from apps.api.job_store import JobStore
from portfolio_lab.backtest import BacktestEngine
from portfolio_lab.models import BacktestSpec, PortfolioSpec, RebalanceFrequency, to_primitive


class BacktestWorker:
    def __init__(self, data_dir: str | Path = "data", store: JobStore | None = None) -> None:
        self.data_dir = Path(data_dir)
        self.store = store or JobStore(self.data_dir)
        self.engine = BacktestEngine(self.data_dir)

    def run_once(self) -> bool:
        job = self.store.claim_next_queued()
        if not job:
            return False

        payload = job["payload"]
        job_id = job["job_id"]

        try:
            result = self.engine.run(
                PortfolioSpec(
                    weights=payload["weights"],
                    base_currency=payload.get("base_currency", "CNY"),
                ),
                BacktestSpec(
                    snapshot_id=payload["snapshot_id"],
                    start_date=date.fromisoformat(payload["start_date"]),
                    end_date=date.fromisoformat(payload["end_date"]),
                    rebalance_frequency=RebalanceFrequency(payload["rebalance_frequency"]),
                    base_currency=payload.get("base_currency", "CNY"),
                ),
            )
            self.store.save_result(
                job_id,
                {
                    "job_id": job_id,
                    "run_id": result.run_id,
                    "snapshot_id": result.metadata.snapshot_id,
                    "metrics": result.metrics,
                    "equity_curve": to_primitive(result.equity_curve),
                    "metadata": to_primitive(result.metadata),
                },
            )
            self.store.mark_completed(job_id, result.run_id)
        except Exception as exc:
            self.store.mark_failed(job_id, str(exc))

        return True

    def run_forever(self, poll_seconds: float = 1.0) -> None:
        while True:
            processed = self.run_once()
            if not processed:
                time.sleep(poll_seconds)


if __name__ == "__main__":
    worker = BacktestWorker()
    worker.run_forever()
