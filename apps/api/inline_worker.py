"""Inline worker that processes a single job synchronously within the API request."""

from __future__ import annotations

from datetime import date
from typing import Any

from portfolio_lab.backtest import BacktestEngine
from portfolio_lab.models import BacktestSpec, PortfolioSpec, RebalanceFrequency, to_primitive

from .job_store import JobStore


class InlineWorker:
    """Run a backtest job synchronously. Used by /jobs/auto to return results immediately."""

    def __init__(self, store: JobStore) -> None:
        self.store = store
        self.engine = BacktestEngine(store.base_dir)

    def process_job(self, job_id: str) -> None:
        job = self.store.claim_next_queued()
        if not job or job["job_id"] != job_id:
            return

        payload = job["payload"]
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
