"""Backtest engine implementation."""

from __future__ import annotations

import hashlib
import json
import socket
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from .analysis import analyze_run
from .construction import deterministic_portfolio_id, validate_fixed_weight_portfolio
from .errors import MissingDataError, NetworkAccessError, SnapshotError, ValidationError
from .models import (
    AssetDefinition,
    BacktestSpec,
    CalendarType,
    EquityPoint,
    ExperimentRunMetadata,
    PortfolioSpec,
    RebalanceFrequency,
    SingleRunResult,
    to_primitive,
)
from .universe import is_trading_day, verify_snapshot_integrity


def _parse_date(raw: str) -> date:
    return date.fromisoformat(raw)


class BacktestEngine:
    """Offline-only backtest engine using immutable snapshots."""

    def __init__(self, data_dir: str | Path = "data", engine_version: str = "0.1.0") -> None:
        self.data_dir = Path(data_dir)
        self.snapshot_dir = self.data_dir / "snapshots"
        self.run_dir = self.data_dir / "runs"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.engine_version = engine_version

    @contextmanager
    def _deny_outbound_network(self) -> Iterator[None]:
        original_create_connection = socket.create_connection
        original_connect = socket.socket.connect

        def blocked(*args, **kwargs):
            raise NetworkAccessError("outbound market-data API access is disabled during backtest")

        socket.create_connection = blocked
        socket.socket.connect = blocked
        try:
            yield
        finally:
            socket.create_connection = original_create_connection
            socket.socket.connect = original_connect

    def _load_snapshot(self, snapshot_id: str) -> dict:
        path = self.snapshot_dir / f"{snapshot_id}.json"
        if not path.exists():
            raise SnapshotError(f"snapshot not found: {snapshot_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        verify_snapshot_integrity(payload)
        return payload

    @staticmethod
    def _iter_days(start: date, end: date) -> Iterator[date]:
        current = start
        while current <= end:
            yield current
            current += timedelta(days=1)

    @staticmethod
    def _is_rebalance_day(day: date, frequency: RebalanceFrequency, start_date: date) -> bool:
        if day == start_date:
            return True
        if frequency == RebalanceFrequency.NONE:
            return False
        if frequency == RebalanceFrequency.MONTHLY:
            return day.day == 1
        if frequency == RebalanceFrequency.QUARTERLY:
            return day.day == 1 and day.month in {1, 4, 7, 10}
        return False

    @staticmethod
    def _fx_is_expected(day: date) -> bool:
        return day.weekday() < 5

    def _resolve_fx_rate(
        self,
        fx_data: dict,
        quote_currency: str,
        base_currency: str,
        day: date,
    ) -> tuple[float, bool]:
        if quote_currency == base_currency:
            return 1.0, False

        pair = f"{quote_currency}/{base_currency}"
        pair_series = fx_data.get(pair)
        if not pair_series:
            raise MissingDataError(f"missing fx pair in snapshot: {pair}")

        day_key = day.isoformat()
        if day_key in pair_series:
            return float(pair_series[day_key]["rate"]), False

        if self._fx_is_expected(day):
            raise MissingDataError(f"missing FX on expected day: {pair} {day_key}")

        # weekend/closed day stale handling
        previous_days = sorted(d for d in pair_series.keys() if d < day_key)
        if not previous_days:
            raise MissingDataError(f"no historical FX to support stale valuation: {pair} {day_key}")
        return float(pair_series[previous_days[-1]]["rate"]), True

    def _resolve_asset_price(
        self,
        asset: AssetDefinition,
        price_series: dict,
        day: date,
    ) -> tuple[float, bool, bool]:
        """Return (price, is_stale, market_closed).

        On a trading day with no price, look back up to 10 days for the most
        recent known price and mark it stale.  The 10-day window covers long
        holidays (Chinese New Year, National Day).  Raise only when no price
        exists within the lookback window.
        """
        day_key = day.isoformat()
        if day_key in price_series:
            return float(price_series[day_key]["close"]), False, False

        trading_day = is_trading_day(day, CalendarType(asset["calendar"]))

        # Look backward for the most recent price
        previous_days = sorted(d for d in price_series.keys() if d < day_key)
        if previous_days:
            last_day = previous_days[-1]
            gap = (day - date.fromisoformat(last_day)).days
            if trading_day and gap > 10:
                raise MissingDataError(
                    f"missing price on expected trading day (no data within 10-day lookback): "
                    f"{asset['identifier']} {day_key}"
                )
            return float(price_series[last_day]["close"]), True, not trading_day

        if trading_day:
            raise MissingDataError(f"missing price on expected trading day: {asset['identifier']} {day_key}")

        raise MissingDataError(f"no historical close for stale valuation: {asset['identifier']} {day_key}")

    def run(self, portfolio_spec: PortfolioSpec, backtest_spec: BacktestSpec) -> SingleRunResult:
        if not backtest_spec.snapshot_id:
            raise ValidationError("snapshot_id is required")

        validate_fixed_weight_portfolio(portfolio_spec.weights, portfolio_spec.tolerance)
        snapshot = self._load_snapshot(backtest_spec.snapshot_id)

        assets: dict[str, dict] = snapshot["assets"]
        prices: dict[str, dict] = snapshot["prices"]
        fx_data: dict[str, dict] = snapshot["fx"]

        for asset_id in portfolio_spec.weights:
            if asset_id not in assets:
                raise ValidationError(f"asset not in snapshot: {asset_id}")

        run_id = f"run-{uuid4().hex[:12]}"
        portfolio_id = deterministic_portfolio_id(portfolio_spec.weights)

        input_payload = {
            "portfolio_spec": to_primitive(portfolio_spec),
            "backtest_spec": to_primitive(backtest_spec),
        }
        input_hash = hashlib.sha256(json.dumps(input_payload, sort_keys=True).encode("utf-8")).hexdigest()

        holdings: dict[str, float] = {asset_id: 0.0 for asset_id in portfolio_spec.weights}
        cash = 1.0
        equity_curve: list[EquityPoint] = []
        rebalance_state = {
            "transaction_cost_bps": backtest_spec.transaction_cost_bps,
            "slippage_bps": backtest_spec.slippage_bps,
        }

        with self._deny_outbound_network():
            for day in self._iter_days(backtest_spec.start_date, backtest_spec.end_date):
                stale_assets: list[str] = []
                no_trade_assets: list[str] = []
                asset_values_base: dict[str, float] = {}
                price_lookup: dict[str, float] = {}
                tradable_today: dict[str, bool] = {}

                for asset_id in portfolio_spec.weights:
                    asset = assets[asset_id]
                    asset_price, stale_price, market_closed = self._resolve_asset_price(asset, prices[asset_id], day)
                    fx_rate, stale_fx = self._resolve_fx_rate(
                        fx_data,
                        quote_currency=asset["quote_currency"],
                        base_currency=backtest_spec.base_currency,
                        day=day,
                    )

                    if stale_price or stale_fx:
                        stale_assets.append(asset_id)

                    price_base = asset_price * fx_rate
                    price_lookup[asset_id] = price_base
                    asset_values_base[asset_id] = holdings[asset_id] * price_base
                    tradable_today[asset_id] = not market_closed

                equity = cash + sum(asset_values_base.values())

                if self._is_rebalance_day(day, backtest_spec.rebalance_frequency, backtest_spec.start_date):
                    for asset_id, target_weight in portfolio_spec.weights.items():
                        if not tradable_today[asset_id]:
                            no_trade_assets.append(asset_id)
                            continue

                        target_value = equity * target_weight
                        current_value = asset_values_base[asset_id]
                        diff_value = target_value - current_value
                        trade_qty = diff_value / price_lookup[asset_id] if price_lookup[asset_id] else 0.0

                        trade_notional = abs(diff_value)
                        trade_cost = trade_notional * (
                            rebalance_state["transaction_cost_bps"] + rebalance_state["slippage_bps"]
                        ) / 10000.0

                        holdings[asset_id] += trade_qty
                        cash -= diff_value
                        cash -= trade_cost

                    # recompute post-trade equity based on current prices
                    asset_values_base = {
                        asset_id: holdings[asset_id] * price_lookup[asset_id]
                        for asset_id in portfolio_spec.weights
                    }
                    equity = cash + sum(asset_values_base.values())

                equity_curve.append(
                    EquityPoint(
                        day=day,
                        equity=equity,
                        cash=cash,
                        stale_assets=sorted(set(stale_assets)),
                        no_trade_assets=sorted(set(no_trade_assets)),
                    )
                )

        metadata = ExperimentRunMetadata(
            run_id=run_id,
            snapshot_id=backtest_spec.snapshot_id,
            created_at=datetime.now(timezone.utc),
            input_hash=input_hash,
            data_version=snapshot["snapshot_id"],
            engine_version=self.engine_version,
            assumptions={
                "calendar_alignment": "asset-calendar-driven with stale valuation on market-closed days",
                "missing_data_policy": "fail_fast_on_expected_trading_days",
                "metric_parameters": {
                    "trading_days_per_year": 252,
                    "risk_free_rate": 0.0,
                },
            },
        )

        result = SingleRunResult(
            run_id=run_id,
            portfolio_id=portfolio_id,
            metadata=metadata,
            equity_curve=equity_curve,
            metrics={},
        )
        result.metrics = analyze_run(result)["metrics"]
        self._persist_run(result, portfolio_spec, backtest_spec)
        return result

    def _persist_run(self, result: SingleRunResult, portfolio_spec: PortfolioSpec, backtest_spec: BacktestSpec) -> None:
        out_file = self.run_dir / f"{result.run_id}.json"
        payload = {
            "result": to_primitive(result),
            "input": {
                "portfolio_spec": to_primitive(portfolio_spec),
                "backtest_spec": to_primitive(backtest_spec),
            },
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        out_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
