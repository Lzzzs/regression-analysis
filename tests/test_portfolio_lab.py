from __future__ import annotations

import json
import socket
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from portfolio_lab.analysis import analyze_run, compare_across_windows, rank_batch
from portfolio_lab.backtest import BacktestEngine
from portfolio_lab.construction import (
    PortfolioGenerationConstraints,
    WeightRange,
    deterministic_portfolio_id,
    generate_portfolios,
    validate_fixed_weight_portfolio,
)
from portfolio_lab.errors import (
    DuplicateAssetError,
    MissingDataError,
    NetworkAccessError,
    SnapshotError,
    ValidationError,
)
from portfolio_lab.models import (
    AssetDefinition,
    AssetType,
    BacktestSpec,
    CalendarType,
    PortfolioSpec,
    RebalanceFrequency,
)
from portfolio_lab.data_adapters import LocalJSONMarketDataAdapter, RoutedMarketDataAdapter
from portfolio_lab.universe import UniverseStore, snapshot_checksum


class StubPriceProvider:
    def __init__(self, name: str, rows_by_symbol: dict[str, list[dict]]) -> None:
        self.name = name
        self.rows_by_symbol = {k.upper(): list(v) for k, v in rows_by_symbol.items()}

    def fetch_price_rows(self, start_date: date, end_date: date, symbol: str) -> list[dict]:
        normalized = symbol.upper()
        rows = self.rows_by_symbol.get(normalized, [])
        out: list[dict] = []
        for row in rows:
            day = row["day"] if isinstance(row["day"], date) else date.fromisoformat(str(row["day"]))
            if start_date <= day <= end_date:
                out.append({"day": day, "close": row["close"], "source": row.get("source")})
        return out


class StubFXProvider:
    def __init__(self, name: str, rows_by_pair: dict[str, list[dict]]) -> None:
        self.name = name
        self.rows_by_pair = {k.upper(): list(v) for k, v in rows_by_pair.items()}

    def fetch_fx_rows(self, start_date: date, end_date: date, pair: str) -> list[dict]:
        normalized = pair.upper()
        rows = self.rows_by_pair.get(normalized, [])
        out: list[dict] = []
        for row in rows:
            day = row["day"] if isinstance(row["day"], date) else date.fromisoformat(str(row["day"]))
            if start_date <= day <= end_date:
                out.append({"day": day, "rate": row["rate"], "source": row.get("source")})
        return out


class PortfolioLabTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name) / "data"
        self.store = UniverseStore(self.data_dir)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _register_default_assets(self) -> None:
        self.store.register_asset(
            AssetDefinition("CSI300", AssetType.INDEX, "CN", CalendarType.A_SHARE, "CNY")
        )
        self.store.register_asset(
            AssetDefinition("SPY", AssetType.ETF, "US", CalendarType.US_EQUITY, "USD")
        )
        self.store.register_asset(
            AssetDefinition("BTC", AssetType.CRYPTO, "CRYPTO", CalendarType.CRYPTO_7D, "USD")
        )

    def _seed_market_data(self, start: date, end: date) -> None:
        prices = []
        fx = []
        day = start
        while day <= end:
            if day.weekday() < 5:
                prices.append({"asset_id": "CSI300", "day": day, "close": 4000 + (day - start).days, "source": "fixture"})
                prices.append({"asset_id": "SPY", "day": day, "close": 500 + (day - start).days, "source": "fixture"})
                fx.append({"pair": "USD/CNY", "day": day, "rate": 7.0 + ((day - start).days * 0.001), "source": "fixture"})
            prices.append({"asset_id": "BTC", "day": day, "close": 30000 + 10 * (day - start).days, "source": "fixture"})
            day += timedelta(days=1)
        self.store.ingest_prices(prices)
        self.store.ingest_fx(fx)

    def _publish_default_snapshot(self) -> str:
        coverage_start = date(2026, 1, 5)
        week_end = date(2026, 1, 9)
        self._seed_market_data(coverage_start, week_end)
        return self.store.publish_weekly_snapshot(
            week_end=week_end,
            selected_assets=["CSI300", "SPY", "BTC"],
            required_fx_pairs=["USD/CNY"],
            coverage_start=coverage_start,
        )

    def test_asset_registration_and_duplicate_rejection(self) -> None:
        asset = AssetDefinition("CSI300", AssetType.INDEX, "CN", CalendarType.A_SHARE, "CNY")
        self.store.register_asset(asset)
        with self.assertRaises(DuplicateAssetError):
            self.store.register_asset(asset)

    def test_price_ingestion_row_validation(self) -> None:
        self._register_default_assets()
        with self.assertRaises(ValidationError):
            self.store.ingest_prices([{"asset_id": "CSI300", "day": "2026-01-05", "source": "fixture"}])

    def test_daily_increment_and_weekly_snapshot(self) -> None:
        self._register_default_assets()
        start = date(2026, 1, 5)
        for i in range(5):
            day = start + timedelta(days=i)
            self.store.ingest_daily_increment(
                day=day,
                price_rows=[
                    {"asset_id": "CSI300", "close": 4000 + i, "source": "fixture"},
                    {"asset_id": "SPY", "close": 500 + i, "source": "fixture"},
                    {"asset_id": "BTC", "close": 30000 + i, "source": "fixture"},
                ],
                fx_rows=[{"pair": "USD/CNY", "rate": 7.0 + i * 0.001, "source": "fixture"}],
            )

        snapshot_id = self.store.publish_weekly_snapshot(
            week_end=date(2026, 1, 9),
            selected_assets=["CSI300", "SPY", "BTC"],
            required_fx_pairs=["USD/CNY"],
            coverage_start=start,
        )
        self.assertTrue(snapshot_id.startswith("snap-"))

    def test_ingest_from_local_json_adapter(self) -> None:
        self._register_default_assets()
        prices_path = self.data_dir / "prices_fixture.json"
        fx_path = self.data_dir / "fx_fixture.json"
        prices_rows = [
            {"asset_id": "CSI300", "day": "2026-01-05", "close": 4000, "source": "adapter"},
            {"asset_id": "SPY", "day": "2026-01-05", "close": 500, "source": "adapter"},
            {"asset_id": "CSI300", "day": "2026-01-06", "close": 4001, "source": "adapter"},
            {"asset_id": "SPY", "day": "2026-01-06", "close": 501, "source": "adapter"},
            {"asset_id": "CSI300", "day": "2026-01-07", "close": 4002, "source": "adapter"},
            {"asset_id": "SPY", "day": "2026-01-07", "close": 502, "source": "adapter"},
            {"asset_id": "CSI300", "day": "2026-01-08", "close": 4003, "source": "adapter"},
            {"asset_id": "SPY", "day": "2026-01-08", "close": 503, "source": "adapter"},
            {"asset_id": "CSI300", "day": "2026-01-09", "close": 4004, "source": "adapter"},
            {"asset_id": "SPY", "day": "2026-01-09", "close": 504, "source": "adapter"},
        ]
        fx_rows = [
            {"pair": "USD/CNY", "day": "2026-01-05", "rate": 7.0, "source": "adapter"},
            {"pair": "USD/CNY", "day": "2026-01-06", "rate": 7.001, "source": "adapter"},
            {"pair": "USD/CNY", "day": "2026-01-07", "rate": 7.002, "source": "adapter"},
            {"pair": "USD/CNY", "day": "2026-01-08", "rate": 7.003, "source": "adapter"},
            {"pair": "USD/CNY", "day": "2026-01-09", "rate": 7.004, "source": "adapter"},
        ]
        prices_path.write_text(json.dumps(prices_rows), encoding="utf-8")
        fx_path.write_text(json.dumps(fx_rows), encoding="utf-8")

        adapter = LocalJSONMarketDataAdapter(prices_path, fx_path)
        self.store.ingest_from_adapter(
            adapter=adapter,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 9),
            selected_assets=["CSI300", "SPY"],
            required_fx_pairs=["USD/CNY"],
        )

        snapshot_id = self.store.publish_weekly_snapshot(
            week_end=date(2026, 1, 9),
            selected_assets=["CSI300", "SPY"],
            required_fx_pairs=["USD/CNY"],
            coverage_start=date(2026, 1, 5),
        )
        payload = self.store.load_snapshot(snapshot_id)
        self.assertEqual(payload["traceability"]["sources"], ["adapter"])

    def test_routed_adapter_multi_market_ingestion(self) -> None:
        self._register_default_assets()
        start = date(2026, 1, 5)
        end = date(2026, 1, 9)

        cn_provider = StubPriceProvider(
            "cn-provider",
            {
                "000300.SH": [
                    {"day": "2026-01-05", "close": 4000},
                    {"day": "2026-01-06", "close": 4001},
                    {"day": "2026-01-07", "close": 4002},
                    {"day": "2026-01-08", "close": 4003},
                    {"day": "2026-01-09", "close": 4004},
                ]
            },
        )
        us_provider = StubPriceProvider(
            "us-provider",
            {
                "SPY": [
                    {"day": "2026-01-05", "close": 500},
                    {"day": "2026-01-06", "close": 501},
                    {"day": "2026-01-07", "close": 502},
                    {"day": "2026-01-08", "close": 503},
                    {"day": "2026-01-09", "close": 504},
                ]
            },
        )
        crypto_provider = StubPriceProvider(
            "crypto-provider",
            {
                "BTCUSDT": [
                    {"day": "2026-01-05", "close": 30000},
                    {"day": "2026-01-06", "close": 30010},
                    {"day": "2026-01-07", "close": 30020},
                    {"day": "2026-01-08", "close": 30030},
                    {"day": "2026-01-09", "close": 30040},
                ]
            },
        )
        fx_provider = StubFXProvider(
            "fx-provider",
            {
                "USD/CNY": [
                    {"day": "2026-01-05", "rate": 7.0},
                    {"day": "2026-01-06", "rate": 7.001},
                    {"day": "2026-01-07", "rate": 7.002},
                    {"day": "2026-01-08", "rate": 7.003},
                    {"day": "2026-01-09", "rate": 7.004},
                ]
            },
        )
        adapter = RoutedMarketDataAdapter(
            providers_by_market={"CN": cn_provider, "US": us_provider, "CRYPTO": crypto_provider},
            fx_provider=fx_provider,
            asset_market_map={"CSI300": "CN", "SPY": "US", "BTC": "CRYPTO"},
            asset_symbol_map={"CSI300": "000300.SH", "SPY": "SPY", "BTC": "BTCUSDT"},
        )
        self.store.ingest_from_adapter(
            adapter=adapter,
            start_date=start,
            end_date=end,
            selected_assets=["CSI300", "SPY", "BTC"],
            required_fx_pairs=["USD/CNY"],
        )

        snapshot_id = self.store.publish_weekly_snapshot(
            week_end=end,
            selected_assets=["CSI300", "SPY", "BTC"],
            required_fx_pairs=["USD/CNY"],
            coverage_start=start,
        )
        payload = self.store.load_snapshot(snapshot_id)
        self.assertEqual(
            payload["traceability"]["sources"],
            ["cn-provider", "crypto-provider", "fx-provider", "us-provider"],
        )

    def test_routed_adapter_rejects_missing_market_provider(self) -> None:
        self._register_default_assets()
        adapter = RoutedMarketDataAdapter(
            providers_by_market={"US": StubPriceProvider("us-provider", {"SPY": []})},
            fx_provider=StubFXProvider("fx-provider", {}),
            asset_market_map={"CSI300": "CN", "SPY": "US"},
            asset_symbol_map={"CSI300": "000300.SH", "SPY": "SPY"},
        )
        with self.assertRaises(ValidationError):
            self.store.ingest_from_adapter(
                adapter=adapter,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                selected_assets=["CSI300"],
                required_fx_pairs=[],
            )

    def test_price_ingestion_rejects_conflicting_duplicate_keys(self) -> None:
        self._register_default_assets()
        with self.assertRaises(ValidationError):
            self.store.ingest_prices(
                [
                    {"asset_id": "SPY", "day": "2026-01-05", "close": 500, "source": "fixture-a"},
                    {"asset_id": "SPY", "day": "2026-01-05", "close": 501, "source": "fixture-b"},
                ]
            )

    def test_price_ingestion_rejects_weekend_non_crypto(self) -> None:
        self._register_default_assets()
        with self.assertRaises(ValidationError):
            self.store.ingest_prices(
                [{"asset_id": "SPY", "day": "2026-01-10", "close": 500, "source": "fixture"}]
            )

    def test_snapshot_quality_gate_rejects_trading_day_gap(self) -> None:
        self._register_default_assets()
        coverage_start = date(2026, 1, 5)
        week_end = date(2026, 1, 9)
        self._seed_market_data(coverage_start, week_end)

        # remove SPY price for Wednesday to create expected-trading-day gap
        del self.store.prices["SPY"][date(2026, 1, 7)]

        with self.assertRaises(SnapshotError):
            self.store.publish_weekly_snapshot(
                week_end=week_end,
                selected_assets=["CSI300", "SPY", "BTC"],
                required_fx_pairs=["USD/CNY"],
                coverage_start=coverage_start,
            )

    def test_query_asset_metadata(self) -> None:
        self._register_default_assets()
        metadata = self.store.query_assets(["SPY", "CSI300"])
        self.assertEqual(len(metadata), 2)
        self.assertEqual(metadata[0]["quote_currency"], "USD")

    def test_portfolio_validation_and_generation_constraints(self) -> None:
        validate_fixed_weight_portfolio({"SPY": 0.5, "BTC": 0.5})
        with self.assertRaises(ValidationError):
            validate_fixed_weight_portfolio({"SPY": 0.8, "BTC": 0.3})

        constraints = PortfolioGenerationConstraints(btc_cap=0.2)
        ranges = {
            "BTC": WeightRange(0.0, 0.3, 0.1),
            "SPY": WeightRange(0.7, 1.0, 0.1),
        }
        candidates = generate_portfolios(ranges, constraints)
        self.assertTrue(candidates)
        self.assertTrue(all(p["BTC"] <= 0.2 for p in candidates))

    def test_deterministic_portfolio_id(self) -> None:
        p1 = {"SPY": 0.6, "BTC": 0.4}
        p2 = {"BTC": 0.4, "SPY": 0.6}
        self.assertEqual(deterministic_portfolio_id(p1), deterministic_portfolio_id(p2))

    def test_backtest_requires_snapshot_id(self) -> None:
        with self.assertRaises(ValidationError):
            BacktestSpec(
                snapshot_id="",
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.MONTHLY,
            )

    def test_network_guard_blocks_outbound_calls(self) -> None:
        engine = BacktestEngine(self.data_dir)
        with engine._deny_outbound_network():
            with self.assertRaises(NetworkAccessError):
                socket.create_connection(("example.com", 80), timeout=0.1)

    def test_backtest_tolerates_minor_price_gap(self) -> None:
        """A single missing trading day within the 5-day lookback is tolerated."""
        self._register_default_assets()
        snapshot_id = self._publish_default_snapshot()
        snapshot_file = self.data_dir / "snapshots" / f"{snapshot_id}.json"
        payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
        del payload["prices"]["SPY"]["2026-01-07"]
        payload["integrity"]["checksum_sha256"] = snapshot_checksum(payload)
        snapshot_file.write_text(json.dumps(payload), encoding="utf-8")

        engine = BacktestEngine(self.data_dir)
        # Should NOT raise — the lookback finds a price within 5 days
        result = engine.run(
            PortfolioSpec(weights={"SPY": 0.5, "CSI300": 0.5}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.MONTHLY,
                base_currency="CNY",
            ),
        )
        self.assertIsNotNone(result)

    def test_backtest_fail_fast_on_missing_price_beyond_lookback(self) -> None:
        """When all prices except a distant one are removed, the 5-day lookback fails."""
        self._register_default_assets()
        snapshot_id = self._publish_default_snapshot()
        snapshot_file = self.data_dir / "snapshots" / f"{snapshot_id}.json"
        payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
        # Remove all SPY prices so no lookback is possible for any trading day
        payload["prices"]["SPY"] = {}
        payload["integrity"]["checksum_sha256"] = snapshot_checksum(payload)
        snapshot_file.write_text(json.dumps(payload), encoding="utf-8")

        engine = BacktestEngine(self.data_dir)
        with self.assertRaises(MissingDataError):
            engine.run(
                PortfolioSpec(weights={"SPY": 0.5, "CSI300": 0.5}, base_currency="CNY"),
                BacktestSpec(
                    snapshot_id=snapshot_id,
                    start_date=date(2026, 1, 5),
                    end_date=date(2026, 1, 9),
                    rebalance_frequency=RebalanceFrequency.MONTHLY,
                    base_currency="CNY",
                ),
            )

    def test_tampered_snapshot_integrity_rejected(self) -> None:
        self._register_default_assets()
        snapshot_id = self._publish_default_snapshot()
        snapshot_file = self.data_dir / "snapshots" / f"{snapshot_id}.json"
        payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
        payload["prices"]["SPY"]["2026-01-07"]["close"] = 999999
        snapshot_file.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(SnapshotError):
            self.store.load_snapshot(snapshot_id)

        engine = BacktestEngine(self.data_dir)
        with self.assertRaises(SnapshotError):
            engine.run(
                PortfolioSpec(weights={"SPY": 1.0}, base_currency="CNY"),
                BacktestSpec(
                    snapshot_id=snapshot_id,
                    start_date=date(2026, 1, 5),
                    end_date=date(2026, 1, 9),
                    rebalance_frequency=RebalanceFrequency.MONTHLY,
                    base_currency="CNY",
                ),
            )

    def test_market_closed_day_stale_valuation_and_no_trade(self) -> None:
        self._register_default_assets()
        # include Friday + weekend
        self._seed_market_data(date(2026, 1, 2), date(2026, 1, 9))
        snapshot_id = self.store.publish_weekly_snapshot(
            week_end=date(2026, 1, 9),
            selected_assets=["SPY", "BTC", "CSI300"],
            required_fx_pairs=["USD/CNY"],
            coverage_start=date(2026, 1, 2),
        )

        engine = BacktestEngine(self.data_dir)
        result = engine.run(
            PortfolioSpec(weights={"SPY": 1.0}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=snapshot_id,
                start_date=date(2026, 1, 3),  # Saturday
                end_date=date(2026, 1, 3),
                rebalance_frequency=RebalanceFrequency.MONTHLY,
                base_currency="CNY",
            ),
        )
        point = result.equity_curve[0]
        self.assertIn("SPY", point.stale_assets)
        self.assertIn("SPY", point.no_trade_assets)

    def test_analysis_and_batch_comparison(self) -> None:
        self._register_default_assets()
        snapshot_id = self._publish_default_snapshot()
        engine = BacktestEngine(self.data_dir)

        run_a = engine.run(
            PortfolioSpec(weights={"SPY": 0.6, "CSI300": 0.4}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.MONTHLY,
                base_currency="CNY",
            ),
        )
        run_b = engine.run(
            PortfolioSpec(weights={"SPY": 0.2, "CSI300": 0.8}, base_currency="CNY"),
            BacktestSpec(
                snapshot_id=snapshot_id,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 9),
                rebalance_frequency=RebalanceFrequency.NONE,
                base_currency="CNY",
            ),
        )

        analyzed = analyze_run(run_a)
        self.assertIn("max_drawdown", analyzed["metrics"])
        self.assertIn("drawdown_series", analyzed)

        ranking = rank_batch([run_a, run_b], "calmar_ratio")
        self.assertEqual(len(ranking.ranking), 2)

        window_compare = compare_across_windows([run_a, run_b], run_a.portfolio_id)
        self.assertEqual(len(window_compare), 1)

    def test_end_to_end_fixture_mixed_currency_and_constraints(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "mixed_currency_dataset.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

        self.store.register_asset(
            AssetDefinition("CSI300", AssetType.INDEX, "CN", CalendarType.A_SHARE, "CNY")
        )
        self.store.register_asset(
            AssetDefinition("SPY", AssetType.ETF, "US", CalendarType.US_EQUITY, "USD")
        )
        self.store.register_asset(
            AssetDefinition("BTC", AssetType.CRYPTO, "CRYPTO", CalendarType.CRYPTO_7D, "USD")
        )

        start = date.fromisoformat(fixture["coverage_start"])
        week_end = date.fromisoformat(fixture["week_end"])
        self._seed_market_data(start, week_end)
        snapshot_id = self.store.publish_weekly_snapshot(
            week_end=week_end,
            selected_assets=["CSI300", "SPY", "BTC"],
            required_fx_pairs=[fixture["fx_pair"]],
            coverage_start=start,
        )

        constraints = PortfolioGenerationConstraints(btc_cap=0.2)
        candidates = generate_portfolios(
            {
                "CSI300": WeightRange(0.4, 0.8, 0.2),
                "SPY": WeightRange(0.2, 0.6, 0.2),
                "BTC": WeightRange(0.0, 0.2, 0.1),
            },
            constraints,
        )
        self.assertTrue(candidates)

        engine = BacktestEngine(self.data_dir)
        run = engine.run(
            PortfolioSpec(weights=candidates[0], base_currency="CNY"),
            BacktestSpec(
                snapshot_id=snapshot_id,
                start_date=start,
                end_date=week_end,
                rebalance_frequency=RebalanceFrequency.MONTHLY,
                base_currency="CNY",
            ),
        )

        self.assertIn("sharpe_ratio", run.metrics)
        saved_run_file = self.data_dir / "runs" / f"{run.run_id}.json"
        self.assertTrue(saved_run_file.exists())


if __name__ == "__main__":
    unittest.main()
