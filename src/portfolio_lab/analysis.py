"""Performance analysis utilities."""

from __future__ import annotations

import math
from datetime import date

from .models import BatchRunResult, SingleRunResult


def _equity_values(run: SingleRunResult) -> list[float]:
    return [p.equity for p in run.equity_curve]


def _returns(values: list[float]) -> list[float]:
    if len(values) < 2:
        return []
    result: list[float] = []
    for idx in range(1, len(values)):
        prev = values[idx - 1]
        curr = values[idx]
        result.append((curr / prev) - 1.0 if prev else 0.0)
    return result


def _max_drawdown(values: list[float]) -> tuple[float, list[float]]:
    peak = float("-inf")
    max_dd = 0.0
    series: list[float] = []
    for val in values:
        peak = max(peak, val)
        dd = (val / peak) - 1.0 if peak > 0 else 0.0
        series.append(dd)
        max_dd = min(max_dd, dd)
    return max_dd, series


def _longest_drawdown_duration(drawdown_series: list[float]) -> int:
    longest = 0
    current = 0
    for dd in drawdown_series:
        if dd < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def analyze_run(
    run: SingleRunResult,
    trading_days_per_year: int = 252,
    risk_free_rate: float = 0.0,
) -> dict:
    values = _equity_values(run)
    rets = _returns(values)

    cumulative_return = (values[-1] / values[0]) - 1.0 if len(values) >= 2 else 0.0
    years = (len(rets) / trading_days_per_year) if rets else 0.0
    annualized_return = ((1 + cumulative_return) ** (1 / years) - 1.0) if years > 0 else 0.0
    annualized_vol = _std(rets) * math.sqrt(trading_days_per_year) if rets else 0.0

    max_dd, drawdown_series = _max_drawdown(values if values else [1.0])
    drawdown_duration = _longest_drawdown_duration(drawdown_series)

    downside = [r for r in rets if r < 0]
    downside_vol = _std(downside) * math.sqrt(trading_days_per_year) if downside else 0.0

    sharpe = (annualized_return - risk_free_rate) / annualized_vol if annualized_vol > 0 else 0.0
    sortino = (annualized_return - risk_free_rate) / downside_vol if downside_vol > 0 else 0.0
    calmar = annualized_return / abs(max_dd) if max_dd < 0 else 0.0

    return {
        "metrics": {
            "cumulative_return": cumulative_return,
            "annualized_return": annualized_return,
            "annualized_volatility": annualized_vol,
            "max_drawdown": max_dd,
            "drawdown_duration_days": float(drawdown_duration),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
        },
        "drawdown_series": drawdown_series,
        "assumptions": {
            "trading_days_per_year": trading_days_per_year,
            "risk_free_rate": risk_free_rate,
        },
    }


def rank_batch(runs: list[SingleRunResult], objective: str) -> BatchRunResult:
    objective = objective.strip().lower()
    ranking = []
    for run in runs:
        metric = run.metrics.get(objective)
        if metric is None:
            raise ValueError(f"metric not found for ranking: {objective}")
        ranking.append(
            {
                "run_id": run.run_id,
                "portfolio_id": run.portfolio_id,
                "value": metric,
            }
        )
    ranking.sort(key=lambda row: row["value"], reverse=True)
    return BatchRunResult(objective=objective, runs=runs, ranking=ranking)


def compare_across_windows(runs: list[SingleRunResult], portfolio_id: str) -> list[dict]:
    target = [run for run in runs if run.portfolio_id == portfolio_id]
    target.sort(key=lambda run: run.equity_curve[0].day if run.equity_curve else date.min)
    return [
        {
            "run_id": run.run_id,
            "portfolio_id": run.portfolio_id,
            "window_start": run.equity_curve[0].day.isoformat() if run.equity_curve else None,
            "window_end": run.equity_curve[-1].day.isoformat() if run.equity_curve else None,
            "metrics": run.metrics,
        }
        for run in target
    ]
