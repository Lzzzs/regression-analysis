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
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
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
        "yearly_returns": yearly_returns(run),
        "drawdown_series": drawdown_series,
        "assumptions": {
            "trading_days_per_year": trading_days_per_year,
            "risk_free_rate": risk_free_rate,
        },
    }


def top_drawdown_events(run: SingleRunResult, n: int = 5) -> list[dict]:
    """Find the top N drawdown events by magnitude.

    Returns list of dicts: [{start_date, trough_date, end_date, drawdown, duration_days}].
    end_date is when equity recovers to the pre-drawdown peak (None if not recovered).
    """
    if len(run.equity_curve) < 2:
        return []

    events: list[dict] = []
    peak = run.equity_curve[0].equity
    peak_date = run.equity_curve[0].day
    in_drawdown = False
    trough = peak
    trough_date = peak_date
    dd_start_date = peak_date

    for pt in run.equity_curve:
        if pt.equity >= peak:
            if in_drawdown:
                # Recovered — close this drawdown event
                dd = (trough / peak - 1.0) if peak > 0 else 0.0
                events.append({
                    "start_date": dd_start_date.isoformat(),
                    "trough_date": trough_date.isoformat(),
                    "end_date": pt.day.isoformat(),
                    "drawdown": dd,
                    "duration_days": (pt.day - dd_start_date).days,
                })
                in_drawdown = False
            peak = pt.equity
            peak_date = pt.day
            trough = peak
            trough_date = peak_date
        else:
            if not in_drawdown:
                in_drawdown = True
                dd_start_date = peak_date
            if pt.equity < trough:
                trough = pt.equity
                trough_date = pt.day

    # If still in drawdown at end of curve
    if in_drawdown:
        dd = (trough / peak - 1.0) if peak > 0 else 0.0
        events.append({
            "start_date": dd_start_date.isoformat(),
            "trough_date": trough_date.isoformat(),
            "end_date": None,
            "drawdown": dd,
            "duration_days": (run.equity_curve[-1].day - dd_start_date).days,
        })

    events.sort(key=lambda e: e["drawdown"])
    return events[:n]


def yearly_returns(run: SingleRunResult) -> list[dict]:
    """Compute per-year return breakdown from the equity curve.

    Returns a list of dicts: [{year, start_equity, end_equity, return}].
    """
    if len(run.equity_curve) < 2:
        return []

    by_year: dict[int, list] = {}
    for pt in run.equity_curve:
        by_year.setdefault(pt.day.year, []).append(pt)

    result = []
    for year in sorted(by_year):
        pts = by_year[year]
        first = pts[0].equity
        last = pts[-1].equity
        ret = (last / first - 1.0) if first > 0 else 0.0
        result.append({
            "year": year,
            "start_equity": first,
            "end_equity": last,
            "return": ret,
        })
    return result


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
