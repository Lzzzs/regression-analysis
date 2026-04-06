"""Golden case regression tests for the backtest engine.

Each test uses deterministic fixture data with hand-computed expected values.
If any expected value drifts beyond tolerance after a code change, it means
the engine's core calculation logic has regressed.

These tests are designed for use with the auto-iterate program (program.md).
Gate 2 relies on these to catch regressions in the backtest engine.

Data setup (shared across cases):
  - CSI300: A-share index, CNY, prices 4000..4004 on Mon-Fri 2026-01-05~09
  - SPY:    US ETF, USD, prices 500..504 on Mon-Fri 2026-01-05~09
  - BTC:    Crypto, USD, prices 30000..30080 every day (including weekends)
  - USD/CNY: 7.000..7.004 on weekdays
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from portfolio_lab.backtest import BacktestEngine
from portfolio_lab.models import (
    AssetDefinition,
    AssetType,
    BacktestSpec,
    CalendarType,
    PortfolioSpec,
    RebalanceFrequency,
)
from portfolio_lab.universe import UniverseStore

# ---------------------------------------------------------------------------
# Tolerance: 1e-6 relative error — tight enough to catch real bugs,
# loose enough to absorb float rounding across platforms.
# ---------------------------------------------------------------------------
REL_TOL = 1e-6


def _assert_close(test: unittest.TestCase, actual: float, expected: float, label: str) -> None:
    """Assert two floats are equal within relative tolerance."""
    if expected == 0.0:
        test.assertAlmostEqual(actual, expected, places=8, msg=f"{label}: {actual} != {expected}")
    else:
        rel_err = abs(actual - expected) / abs(expected)
        test.assertLess(
            rel_err, REL_TOL,
            msg=f"{label}: actual={actual:.12f}, expected={expected:.12f}, rel_err={rel_err:.2e}",
        )


class GoldenCaseBase(unittest.TestCase):
    """Shared setup: register assets, seed prices, publish snapshot."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name) / "data"
        self.store = UniverseStore(self.data_dir)

        # Register assets
        self.store.register_asset(
            AssetDefinition("CSI300", AssetType.INDEX, "CN", CalendarType.A_SHARE, "CNY")
        )
        self.store.register_asset(
            AssetDefinition("SPY", AssetType.ETF, "US", CalendarType.US_EQUITY, "USD")
        )
        self.store.register_asset(
            AssetDefinition("BTC", AssetType.CRYPTO, "CRYPTO", CalendarType.CRYPTO_7D, "USD")
        )

        # Seed deterministic price data: 2026-01-05 (Mon) to 2026-01-09 (Fri)
        start = date(2026, 1, 5)
        end = date(2026, 1, 9)
        prices = []
        fx = []
        day = start
        while day <= end:
            offset = (day - start).days
            if day.weekday() < 5:  # weekday
                prices.append({
                    "asset_id": "CSI300", "day": day,
                    "close": 4000 + offset, "source": "golden",
                })
                prices.append({
                    "asset_id": "SPY", "day": day,
                    "close": 500 + offset, "source": "golden",
                })
                fx.append({
                    "pair": "USD/CNY", "day": day,
                    "rate": 7.0 + offset * 0.001, "source": "golden",
                })
            # BTC trades every day
            prices.append({
                "asset_id": "BTC", "day": day,
                "close": 30000 + 10 * offset, "source": "golden",
            })
            day += timedelta(days=1)

        self.store.ingest_prices(prices)
        self.store.ingest_fx(fx)

        self.snapshot_id = self.store.publish_weekly_snapshot(
            week_end=end,
            selected_assets=["CSI300", "SPY", "BTC"],
            required_fx_pairs=["USD/CNY"],
            coverage_start=start,
        )
        self.engine = BacktestEngine(self.data_dir)

    def tearDown(self) -> None:
        self.tmp.cleanup()


class TestGoldenCase1_SingleAssetNoFX(GoldenCaseBase):
    """CSI300 100%, base=CNY, no rebalance, no cost.

    Hand computation:
      Day1: rebalance → buy 1.0/4000 = 0.00025 shares, cash=0
      Day2: equity = 0.00025 * 4001 = 1.000250
      Day3: equity = 0.00025 * 4002 = 1.000500
      Day4: equity = 0.00025 * 4003 = 1.000750
      Day5: equity = 0.00025 * 4004 = 1.001000
    """

    def test_equity_curve(self) -> None:
        result = self.engine.run(
            PortfolioSpec(weights={"CSI300": 1.0}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=self.snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.NONE,
                base_currency="CNY",
            ),
        )

        expected_equity = [1.0, 1.000250, 1.000500, 1.000750, 1.001000]
        self.assertEqual(len(result.equity_curve), 5)
        for i, pt in enumerate(result.equity_curve):
            _assert_close(self, pt.equity, expected_equity[i], f"day{i+1}_equity")

    def test_metrics(self) -> None:
        result = self.engine.run(
            PortfolioSpec(weights={"CSI300": 1.0}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=self.snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.NONE,
                base_currency="CNY",
            ),
        )

        _assert_close(self, result.metrics["cumulative_return"], 0.001, "cumulative_return")
        _assert_close(self, result.metrics["annualized_return"], 0.06499331378, "annualized_return")
        # Monotonically increasing → no drawdown
        self.assertAlmostEqual(result.metrics["max_drawdown"], 0.0, places=10)


class TestGoldenCase2_DualAssetCrossCurrency(GoldenCaseBase):
    """CSI300 50% + SPY 50%, base=CNY, no rebalance, no cost.

    Hand computation:
      Day1: rebalance
        CSI300 price (CNY): 4000     → buy 0.5/4000 = 0.000125 shares
        SPY price (CNY): 500*7.0=3500 → buy 0.5/3500 shares
        cash = 0

      Day2: CSI300_val = 0.000125*4001 = 0.500125
            SPY_val = (0.5/3500) * 501 * 7.001
            equity = CSI300_val + SPY_val

      (continued for Day3..Day5)
    """

    def test_equity_curve(self) -> None:
        result = self.engine.run(
            PortfolioSpec(weights={"CSI300": 0.5, "SPY": 0.5}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=self.snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.NONE,
                base_currency="CNY",
            ),
        )

        spy_qty = 0.5 / (500 * 7.0)  # shares bought at Day 1
        expected = []
        for i in range(5):
            csi_val = 0.000125 * (4000 + i)
            spy_val = spy_qty * (500 + i) * (7.0 + i * 0.001)
            expected.append(csi_val + spy_val)

        self.assertEqual(len(result.equity_curve), 5)
        for i, pt in enumerate(result.equity_curve):
            _assert_close(self, pt.equity, expected[i], f"day{i+1}_equity")

    def test_metrics(self) -> None:
        result = self.engine.run(
            PortfolioSpec(weights={"CSI300": 0.5, "SPY": 0.5}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=self.snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.NONE,
                base_currency="CNY",
            ),
        )

        _assert_close(self, result.metrics["cumulative_return"], 0.004788, "cumulative_return")
        # Monotonically increasing
        self.assertAlmostEqual(result.metrics["max_drawdown"], 0.0, places=10)


class TestGoldenCase3_TransactionCost(GoldenCaseBase):
    """CSI300 100%, base=CNY, no rebalance, cost=10bps txn + 5bps slippage.

    Hand computation:
      Day1: rebalance
        trade_notional = 1.0
        cost = 1.0 * (10+5)/10000 = 0.0015
        buy 0.00025 shares, cash = 1.0 - 1.0 - 0.0015 = -0.0015
        equity = -0.0015 + 0.00025*4000 = 0.9985

      Day2: equity = -0.0015 + 0.00025*4001 = 0.99875
      ...
    """

    def test_equity_curve(self) -> None:
        result = self.engine.run(
            PortfolioSpec(weights={"CSI300": 1.0}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=self.snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.NONE,
                base_currency="CNY",
                transaction_cost_bps=10.0,
                slippage_bps=5.0,
            ),
        )

        cash = -0.0015
        expected = [cash + 0.00025 * (4000 + i) for i in range(5)]

        self.assertEqual(len(result.equity_curve), 5)
        for i, pt in enumerate(result.equity_curve):
            _assert_close(self, pt.equity, expected[i], f"day{i+1}_equity")

    def test_cost_impact(self) -> None:
        """The cumulative return should be lower than the no-cost case by exactly the cost amount."""
        no_cost = self.engine.run(
            PortfolioSpec(weights={"CSI300": 1.0}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=self.snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.NONE,
                base_currency="CNY",
            ),
        )
        with_cost = self.engine.run(
            PortfolioSpec(weights={"CSI300": 1.0}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=self.snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.NONE,
                base_currency="CNY",
                transaction_cost_bps=10.0,
                slippage_bps=5.0,
            ),
        )

        # Final equity difference should be exactly the trading cost (0.0015)
        diff = no_cost.equity_curve[-1].equity - with_cost.equity_curve[-1].equity
        _assert_close(self, diff, 0.0015, "cost_impact")


class TestGoldenCase4_MonthlyRebalance(GoldenCaseBase):
    """CSI300 60% + SPY 40%, base=CNY, monthly rebalance, no cost.

    Over a 5-day window with start on Jan 5 (Mon), rebalance only happens
    on day 1 (start_date is always a rebalance day). Monthly rebalance
    triggers on day.day==1, which doesn't occur in Jan 5-9.
    So this should produce the same result as no-rebalance.
    """

    def test_same_as_no_rebalance(self) -> None:
        spec_args = dict(
            snapshot_id=self.snapshot_id,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 9),
            base_currency="CNY",
        )

        result_monthly = self.engine.run(
            PortfolioSpec(weights={"CSI300": 0.6, "SPY": 0.4}, base_currency="CNY"),
            BacktestSpec(rebalance_frequency=RebalanceFrequency.MONTHLY, **spec_args),
        )
        result_none = self.engine.run(
            PortfolioSpec(weights={"CSI300": 0.6, "SPY": 0.4}, base_currency="CNY"),
            BacktestSpec(rebalance_frequency=RebalanceFrequency.NONE, **spec_args),
        )

        for i in range(len(result_monthly.equity_curve)):
            _assert_close(
                self,
                result_monthly.equity_curve[i].equity,
                result_none.equity_curve[i].equity,
                f"day{i+1}_equity",
            )


class TestGoldenCase5_CryptoSevenDayCalendar(GoldenCaseBase):
    """BTC 100%, base=USD (no FX needed since BTC quotes in USD... but
    base_currency=CNY so we need USD/CNY FX).

    Actually let's test with base=CNY to exercise FX:
      BTC prices: 30000, 30010, 30020, 30030, 30040 (Mon-Fri)
      USD/CNY: 7.000, 7.001, 7.002, 7.003, 7.004

      Day1: rebalance
        BTC in CNY = 30000 * 7.0 = 210000
        buy 1.0/210000 shares
        equity = 1.0

      Day2: BTC in CNY = 30010 * 7.001 = ?
        equity = (1/210000) * 30010 * 7.001
    """

    def test_equity_curve(self) -> None:
        result = self.engine.run(
            PortfolioSpec(weights={"BTC": 1.0}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=self.snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.NONE,
                base_currency="CNY",
            ),
        )

        btc_qty = 1.0 / (30000 * 7.0)
        expected = []
        for i in range(5):
            btc_price = 30000 + 10 * i
            fx_rate = 7.0 + i * 0.001
            expected.append(btc_qty * btc_price * fx_rate)

        self.assertEqual(len(result.equity_curve), 5)
        for i, pt in enumerate(result.equity_curve):
            _assert_close(self, pt.equity, expected[i], f"day{i+1}_equity")


class TestGoldenCase6_Idempotency(GoldenCaseBase):
    """Running the same backtest twice should produce identical metrics."""

    def test_deterministic(self) -> None:
        ps = PortfolioSpec(weights={"CSI300": 0.5, "SPY": 0.5}, base_currency="CNY")
        bs = BacktestSpec(
            snapshot_id=self.snapshot_id,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 9),
            rebalance_frequency=RebalanceFrequency.NONE,
            base_currency="CNY",
        )

        r1 = self.engine.run(ps, bs)
        r2 = self.engine.run(ps, bs)

        for key in r1.metrics:
            _assert_close(self, r2.metrics[key], r1.metrics[key], f"metric_{key}")

        for i in range(len(r1.equity_curve)):
            _assert_close(
                self,
                r2.equity_curve[i].equity,
                r1.equity_curve[i].equity,
                f"equity_day{i+1}",
            )


class TestGoldenCase7_AnalysisMetrics(GoldenCaseBase):
    """Verify analysis.py computes correct metrics for a known equity curve.

    Uses Case 1 (monotonically increasing) to verify:
    - Sharpe should be extremely high (no drawdown, positive return every day)
    - Sortino should be 0 (no negative returns → downside_vol = 0 → sortino = 0)
    - Max drawdown = 0
    - Calmar = 0 (because max_dd = 0, calmar formula returns 0)
    """

    def test_no_drawdown_metrics(self) -> None:
        result = self.engine.run(
            PortfolioSpec(weights={"CSI300": 1.0}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=self.snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.NONE,
                base_currency="CNY",
            ),
        )

        self.assertAlmostEqual(result.metrics["max_drawdown"], 0.0, places=10)
        self.assertEqual(result.metrics["drawdown_duration_days"], 0.0)
        # Sortino = 0 because there are no negative returns (downside_vol = 0)
        self.assertEqual(result.metrics["sortino_ratio"], 0.0)
        # Calmar = 0 because max_dd = 0
        self.assertEqual(result.metrics["calmar_ratio"], 0.0)
        # Sharpe should be positive (positive return, near-zero vol)
        self.assertGreater(result.metrics["sharpe_ratio"], 0)


class TestGoldenCase8_YearlyReturns(GoldenCaseBase):
    """Verify yearly_returns computation.

    All fixture data is in 2026, so yearly_returns should produce a single
    entry for year=2026 with the correct return.
    """

    def test_single_year(self) -> None:
        from portfolio_lab.analysis import yearly_returns

        result = self.engine.run(
            PortfolioSpec(weights={"CSI300": 1.0}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=self.snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.NONE,
                base_currency="CNY",
            ),
        )

        yr = yearly_returns(result)
        self.assertEqual(len(yr), 1)
        self.assertEqual(yr[0]["year"], 2026)
        _assert_close(self, yr[0]["start_equity"], 1.0, "start_equity")
        _assert_close(self, yr[0]["end_equity"], 1.001, "end_equity")
        _assert_close(self, yr[0]["return"], 0.001, "yearly_return")

    def test_monthly_returns(self) -> None:
        from portfolio_lab.analysis import monthly_returns

        result = self.engine.run(
            PortfolioSpec(weights={"CSI300": 1.0}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=self.snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.NONE,
                base_currency="CNY",
            ),
        )

        mr = monthly_returns(result)
        self.assertEqual(len(mr), 1)
        self.assertEqual(mr[0]["year"], 2026)
        self.assertEqual(mr[0]["month"], 1)
        _assert_close(self, mr[0]["return"], 0.001, "monthly_return_jan2026")

    def test_empty_curve(self) -> None:
        from datetime import datetime
        from portfolio_lab.analysis import yearly_returns
        from portfolio_lab.models import SingleRunResult, ExperimentRunMetadata

        empty_result = SingleRunResult(
            run_id="test",
            portfolio_id="test",
            metadata=ExperimentRunMetadata(
                run_id="test", snapshot_id="snap-test",
                created_at=datetime.now(), input_hash="", data_version="", engine_version="",
            ),
            equity_curve=[],
        )
        self.assertEqual(yearly_returns(empty_result), [])


if __name__ == "__main__":
    unittest.main()
