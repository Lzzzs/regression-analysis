from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from apps.api.job_store import JobStore
from apps.api.orchestration import AutoJobOrchestrator
from apps.api.service import JobService
from apps.api.snapshot_service import SnapshotService
from apps.shared.contracts import ContractError
from apps.worker.runner import BacktestWorker
from portfolio_lab.models import AssetDefinition, AssetType, CalendarType
from portfolio_lab.universe import UniverseStore


class FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._lists: dict[str, list[str]] = {}

    def set(self, key: str, value: str) -> None:
        self._kv[key] = value

    def get(self, key: str):
        return self._kv.get(key)

    def rpush(self, key: str, value: str) -> int:
        self._lists.setdefault(key, []).append(value)
        return len(self._lists[key])

    def lpop(self, key: str):
        values = self._lists.get(key, [])
        if not values:
            return None
        return values.pop(0)

    def keys(self, pattern: str):
        if pattern == "jobs:data:*":
            return [k for k in self._kv if k.startswith("jobs:data:")]
        return []


class WebApiWorkerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name) / "data"
        self.store = UniverseStore(self.data_dir)
        self._register_assets()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _register_assets(self) -> None:
        self.store.register_asset(AssetDefinition("CSI300", AssetType.INDEX, "CN", CalendarType.A_SHARE, "CNY"))
        self.store.register_asset(AssetDefinition("SPY", AssetType.ETF, "US", CalendarType.US_EQUITY, "USD"))

    def _prepare_snapshot(self) -> str:
        start = date(2026, 1, 5)
        end = date(2026, 1, 9)
        prices = []
        fx = []
        day = start
        while day <= end:
            if day.weekday() < 5:
                prices.append({"asset_id": "CSI300", "day": day, "close": 4000 + (day - start).days, "source": "fixture"})
                prices.append({"asset_id": "SPY", "day": day, "close": 500 + (day - start).days, "source": "fixture"})
                fx.append({"pair": "USD/CNY", "day": day, "rate": 7.0 + (day - start).days * 0.001, "source": "fixture"})
            day += timedelta(days=1)
        self.store.ingest_prices(prices)
        self.store.ingest_fx(fx)
        return self.store.publish_weekly_snapshot(
            week_end=end,
            selected_assets=["CSI300", "SPY"],
            required_fx_pairs=["USD/CNY"],
            coverage_start=start,
        )

    def _write_provider_fixtures(self) -> dict[str, str]:
        providers_dir = self.data_dir / "providers"
        providers_dir.mkdir(parents=True, exist_ok=True)
        files = {
            "cn_prices": providers_dir / "cn_prices.csv",
            "us_prices": providers_dir / "us_prices.csv",
            "crypto_prices": providers_dir / "crypto_prices.csv",
            "fx_rates": providers_dir / "fx_rates.csv",
        }
        files["cn_prices"].write_text(
            "symbol,day,close,source\n"
            "000300.SH,2026-01-05,4000,cn-csv\n"
            "000300.SH,2026-01-06,4001,cn-csv\n"
            "000300.SH,2026-01-07,4002,cn-csv\n"
            "000300.SH,2026-01-08,4003,cn-csv\n"
            "000300.SH,2026-01-09,4004,cn-csv\n",
            encoding="utf-8",
        )
        files["us_prices"].write_text(
            "symbol,day,close,source\n"
            "SPY,2026-01-05,500,us-csv\n"
            "SPY,2026-01-06,501,us-csv\n"
            "SPY,2026-01-07,502,us-csv\n"
            "SPY,2026-01-08,503,us-csv\n"
            "SPY,2026-01-09,504,us-csv\n",
            encoding="utf-8",
        )
        files["crypto_prices"].write_text(
            "symbol,day,close,source\n"
            "BTCUSDT,2026-01-05,30000,crypto-csv\n"
            "BTCUSDT,2026-01-06,30010,crypto-csv\n"
            "BTCUSDT,2026-01-07,30020,crypto-csv\n"
            "BTCUSDT,2026-01-08,30030,crypto-csv\n"
            "BTCUSDT,2026-01-09,30040,crypto-csv\n",
            encoding="utf-8",
        )
        files["fx_rates"].write_text(
            "pair,day,rate,source\n"
            "USD/CNY,2026-01-05,7.000,fx-csv\n"
            "USD/CNY,2026-01-06,7.001,fx-csv\n"
            "USD/CNY,2026-01-07,7.002,fx-csv\n"
            "USD/CNY,2026-01-08,7.003,fx-csv\n"
            "USD/CNY,2026-01-09,7.004,fx-csv\n",
            encoding="utf-8",
        )
        return {key: str(path) for key, path in files.items()}

    def test_api_worker_happy_path(self) -> None:
        snapshot_id = self._prepare_snapshot()
        service = JobService(JobStore(self.data_dir))
        created = service.create_job(
            {
                "weights": {"CSI300": 0.6, "SPY": 0.4},
                "snapshot_id": snapshot_id,
                "start_date": "2026-01-05",
                "end_date": "2026-01-09",
                "rebalance_frequency": "monthly",
                "base_currency": "CNY",
            }
        )
        job_id = created["job_id"]

        worker = BacktestWorker(self.data_dir)
        self.assertTrue(worker.run_once())

        status = service.job_status(job_id)
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["payload_summary"]["snapshot_id"], snapshot_id)
        self.assertEqual(status["payload_summary"]["weights"], {"CSI300": 0.6, "SPY": 0.4})
        self.assertTrue(status["events"])
        event_types = [event.get("type") for event in status["events"]]
        self.assertIn("created", event_types)
        self.assertIn("started", event_types)
        self.assertIn("completed", event_types)

        result = service.job_result(job_id)
        self.assertEqual(result["snapshot_id"], snapshot_id)
        self.assertIn("annualized_return", result["metrics"])
        self.assertTrue(result["equity_curve"])

        listing = service.list_jobs()
        self.assertGreaterEqual(listing["count"], 1)
        self.assertTrue(any(item["job_id"] == job_id for item in listing["items"]))
        self.assertGreaterEqual(listing["total"], listing["count"])

    def test_invalid_payload_rejected(self) -> None:
        service = JobService(JobStore(self.data_dir))
        with self.assertRaises(ContractError):
            service.create_job(
                {
                    "weights": {"CSI300": 0.7, "SPY": 0.4},
                    "snapshot_id": "",
                    "start_date": "2026-01-05",
                    "end_date": "2026-01-09",
                    "rebalance_frequency": "monthly",
                }
            )

    def test_worker_failure_marked_failed(self) -> None:
        # With max_retries=1: first failure -> queued, second failure -> dead-letter.
        service = JobService(JobStore(self.data_dir, max_retries=1))
        created = service.create_job(
            {
                "weights": {"CSI300": 0.5, "SPY": 0.5},
                "snapshot_id": "missing-snapshot",
                "start_date": "2026-01-05",
                "end_date": "2026-01-09",
                "rebalance_frequency": "monthly",
                "base_currency": "CNY",
            }
        )
        worker = BacktestWorker(self.data_dir)
        self.assertTrue(worker.run_once())
        status = service.job_status(created["job_id"])
        self.assertEqual(status["status"], "queued")
        self.assertEqual(status["retry_count"], 1)
        event_types = [event.get("type") for event in status["events"]]
        self.assertIn("retry_scheduled", event_types)

        self.assertTrue(worker.run_once())
        status = service.job_status(created["job_id"])
        self.assertEqual(status["status"], "dead-letter")
        self.assertIsNotNone(status["error"])
        self.assertEqual(status["max_retries"], 1)
        event_types = [event.get("type") for event in status["events"]]
        self.assertIn("dead_lettered", event_types)

    def test_redis_backend_retry_and_dead_letter(self) -> None:
        fake_redis = FakeRedis()
        store = JobStore(self.data_dir, backend="redis", redis_client=fake_redis, max_retries=1)
        service = JobService(store)
        created = service.create_job(
            {
                "weights": {"CSI300": 0.5, "SPY": 0.5},
                "snapshot_id": "missing-snapshot",
                "start_date": "2026-01-05",
                "end_date": "2026-01-09",
                "rebalance_frequency": "monthly",
                "base_currency": "CNY",
            }
        )

        worker = BacktestWorker(self.data_dir, store=store)
        self.assertTrue(worker.run_once())
        mid = service.job_status(created["job_id"])
        self.assertEqual(mid["status"], "queued")
        self.assertEqual(mid["retry_count"], 1)

        self.assertTrue(worker.run_once())
        final = service.job_status(created["job_id"])
        self.assertEqual(final["status"], "dead-letter")
        self.assertEqual(final["max_retries"], 1)

    def test_dead_letter_list_and_requeue(self) -> None:
        service = JobService(JobStore(self.data_dir, max_retries=0))
        created = service.create_job(
            {
                "weights": {"CSI300": 0.5, "SPY": 0.5},
                "snapshot_id": "missing-snapshot",
                "start_date": "2026-01-05",
                "end_date": "2026-01-09",
                "rebalance_frequency": "monthly",
                "base_currency": "CNY",
            }
        )

        worker = BacktestWorker(self.data_dir)
        self.assertTrue(worker.run_once())
        dead = service.dead_letter_jobs()
        self.assertEqual(dead["count"], 1)
        self.assertEqual(dead["items"][0]["job_id"], created["job_id"])

        requeued = service.requeue_job(created["job_id"])
        self.assertEqual(requeued["status"], "queued")
        self.assertEqual(requeued["remaining_retries"], requeued["max_retries"])
        current = service.job_status(created["job_id"])
        self.assertEqual(current["status"], "queued")
        self.assertEqual(current["retry_count"], 0)

    def test_list_jobs_pagination_and_search(self) -> None:
        service = JobService(JobStore(self.data_dir))
        ids = []
        for _ in range(3):
            created = service.create_job(
                {
                    "weights": {"CSI300": 0.5, "SPY": 0.5},
                    "snapshot_id": "snap-2026-01-09-333313e7",
                    "start_date": "2026-01-05",
                    "end_date": "2026-01-09",
                    "rebalance_frequency": "monthly",
                    "base_currency": "CNY",
                }
            )
            ids.append(created["job_id"])

        page1 = service.list_jobs(limit=2, offset=0)
        page2 = service.list_jobs(limit=2, offset=2)
        self.assertEqual(page1["count"], 2)
        self.assertGreaterEqual(page1["total"], 3)
        self.assertEqual(page2["count"], 1)

        needle = ids[1].split("-")[-1][:4]
        searched = service.list_jobs(q=needle, limit=20, offset=0)
        self.assertTrue(any(needle in item["job_id"] for item in searched["items"]))

    def test_auto_job_orchestration_without_manual_snapshot(self) -> None:
        provider_files = self._write_provider_fixtures()
        store = JobStore(self.data_dir)
        service = JobService(store)
        snapshot_service = SnapshotService(self.data_dir)
        orchestrator = AutoJobOrchestrator(service, snapshot_service)

        created = orchestrator.create_job_auto(
            {
                "weights": {"CSI300": 0.5, "SPY": 0.5},
                "start_date": "2026-01-05",
                "end_date": "2026-01-09",
                "rebalance_frequency": "monthly",
                "base_currency": "CNY",
                "provider_files": provider_files,
            }
        )
        self.assertEqual(created["status"], "queued")
        self.assertTrue(created["snapshot_id"].startswith("snap-"))

        worker = BacktestWorker(self.data_dir, store=store)
        self.assertTrue(worker.run_once())
        status = service.job_status(created["job_id"])
        self.assertEqual(status["status"], "completed")


if __name__ == "__main__":
    unittest.main()
