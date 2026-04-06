"""Shared job execution logic used by both inline worker and background worker."""

from __future__ import annotations

from datetime import date

from portfolio_lab.analysis import monthly_returns, top_drawdown_events, yearly_returns
from portfolio_lab.backtest import BacktestEngine
from portfolio_lab.models import BacktestSpec, PortfolioSpec, RebalanceFrequency, to_primitive

_SUMMARY_KEYS = ["annualized_return", "sharpe_ratio", "max_drawdown"]


def execute_backtest_job(
    job_id: str,
    payload: dict,
    engine: BacktestEngine,
    save_result: callable,
    mark_completed: callable,
    mark_failed: callable,
    update_job: callable | None = None,
) -> None:
    """Run a backtest job and persist results. Shared by inline and background workers."""
    try:
        result = engine.run(
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
        save_result(
            job_id,
            {
                "job_id": job_id,
                "run_id": result.run_id,
                "snapshot_id": result.metadata.snapshot_id,
                "metrics": result.metrics,
                "yearly_returns": yearly_returns(result),
                "monthly_returns": monthly_returns(result),
                "top_drawdowns": top_drawdown_events(result),
                "equity_curve": to_primitive(result.equity_curve),
                "metadata": to_primitive(result.metadata),
            },
        )
        # Store summary metrics on the job record for list-page display
        if update_job:
            summary = {k: result.metrics[k] for k in _SUMMARY_KEYS if k in result.metrics}
            if summary:
                update_job(job_id, result_summary=summary)
        mark_completed(job_id, result.run_id)
    except Exception as exc:
        mark_failed(job_id, str(exc))
