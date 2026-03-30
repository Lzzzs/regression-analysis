from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from apps.api.snapshot_service import SnapshotService
from portfolio_lab.errors import ValidationError


class SnapshotServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.data_dir = self.base / "data"
        self.providers_dir = self.base / "providers"
        self.providers_dir.mkdir(parents=True, exist_ok=True)
        self._write_provider_fixtures()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_provider_fixtures(self) -> None:
        (self.providers_dir / "cn_prices.csv").write_text(
            "symbol,day,close,source\n"
            "000300.SH,2026-01-05,4000,cn-csv\n"
            "000300.SH,2026-01-06,4001,cn-csv\n"
            "000300.SH,2026-01-07,4002,cn-csv\n"
            "000300.SH,2026-01-08,4003,cn-csv\n"
            "000300.SH,2026-01-09,4004,cn-csv\n",
            encoding="utf-8",
        )
        (self.providers_dir / "us_prices.csv").write_text(
            "symbol,day,close,source\n"
            "SPY,2026-01-05,500,us-csv\n"
            "SPY,2026-01-06,501,us-csv\n"
            "SPY,2026-01-07,502,us-csv\n"
            "SPY,2026-01-08,503,us-csv\n"
            "SPY,2026-01-09,504,us-csv\n",
            encoding="utf-8",
        )
        (self.providers_dir / "crypto_prices.csv").write_text(
            "symbol,day,close,source\n"
            "BTCUSDT,2026-01-05,30000,crypto-csv\n"
            "BTCUSDT,2026-01-06,30010,crypto-csv\n"
            "BTCUSDT,2026-01-07,30020,crypto-csv\n"
            "BTCUSDT,2026-01-08,30030,crypto-csv\n"
            "BTCUSDT,2026-01-09,30040,crypto-csv\n",
            encoding="utf-8",
        )
        (self.providers_dir / "fx_rates.csv").write_text(
            "pair,day,rate,source\n"
            "USD/CNY,2026-01-05,7.000,fx-csv\n"
            "USD/CNY,2026-01-06,7.001,fx-csv\n"
            "USD/CNY,2026-01-07,7.002,fx-csv\n"
            "USD/CNY,2026-01-08,7.003,fx-csv\n"
            "USD/CNY,2026-01-09,7.004,fx-csv\n",
            encoding="utf-8",
        )

    def test_create_snapshot_from_providers(self) -> None:
        service = SnapshotService(self.data_dir)
        payload = {
            "coverage_start": "2026-01-05",
            "week_end": "2026-01-09",
            "selected_assets": ["CSI300", "SPY"],
            "required_fx_pairs": ["USD/CNY"],
            "provider_files": {
                "cn_prices": str(self.providers_dir / "cn_prices.csv"),
                "us_prices": str(self.providers_dir / "us_prices.csv"),
                "crypto_prices": str(self.providers_dir / "crypto_prices.csv"),
                "fx_rates": str(self.providers_dir / "fx_rates.csv"),
            },
        }

        out = service.create_snapshot_from_providers(payload)
        self.assertTrue(out["snapshot_id"].startswith("snap-"))
        self.assertEqual(out["integrity"]["algorithm"], "sha256")
        self.assertIn("checksum_sha256", out["integrity"])
        self.assertEqual(out["traceability"]["sources"], ["cn-csv", "fx-csv", "us-csv"])

    def test_missing_provider_file_rejected(self) -> None:
        service = SnapshotService(self.data_dir)
        payload = {
            "coverage_start": "2026-01-05",
            "week_end": "2026-01-09",
            "selected_assets": ["CSI300"],
            "required_fx_pairs": ["USD/CNY"],
            "provider_files": {
                "cn_prices": str(self.providers_dir / "missing.csv"),
                "us_prices": str(self.providers_dir / "us_prices.csv"),
                "crypto_prices": str(self.providers_dir / "crypto_prices.csv"),
                "fx_rates": str(self.providers_dir / "fx_rates.csv"),
            },
        }
        with self.assertRaises(ValidationError):
            service.create_snapshot_from_providers(payload)


class SnapshotServiceAKSharePathTests(unittest.TestCase):
    """Test the new AKShare-powered path in SnapshotService."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name) / "data"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_akshare_path_builds_snapshot(self):
        """When assets field is provided, use AKShare providers."""
        from datetime import date
        from unittest.mock import MagicMock, patch
        from apps.api.snapshot_service import SnapshotService

        mock_price_provider = MagicMock()
        mock_price_provider.name = "akshare"
        mock_price_provider.fetch_price_rows.return_value = [
            {"day": date(2026, 1, 5), "close": 4000.0, "source": "akshare"},
            {"day": date(2026, 1, 6), "close": 4010.0, "source": "akshare"},
            {"day": date(2026, 1, 7), "close": 4020.0, "source": "akshare"},
            {"day": date(2026, 1, 8), "close": 4030.0, "source": "akshare"},
            {"day": date(2026, 1, 9), "close": 4040.0, "source": "akshare"},
        ]
        mock_fx_provider = MagicMock()
        mock_fx_provider.name = "akshare"
        mock_fx_provider.fetch_fx_rows.return_value = [
            {"day": date(2026, 1, 5), "rate": 7.0, "source": "akshare"},
            {"day": date(2026, 1, 6), "rate": 7.01, "source": "akshare"},
            {"day": date(2026, 1, 7), "rate": 7.02, "source": "akshare"},
            {"day": date(2026, 1, 8), "rate": 7.03, "source": "akshare"},
            {"day": date(2026, 1, 9), "rate": 7.04, "source": "akshare"},
        ]

        with patch(
            "apps.api.snapshot_service.AKSharePriceProvider",
            return_value=mock_price_provider,
        ), patch(
            "apps.api.snapshot_service.AKShareFXProvider",
            return_value=mock_fx_provider,
        ):
            svc = SnapshotService(data_dir=self.data_dir)
            payload = {
                "coverage_start": "2026-01-05",
                "week_end": "2026-01-09",
                "assets": [{"code": "000300", "market": "cn", "asset_type": "stock"}],
                "required_fx_pairs": ["USD/CNY"],
            }
            result = svc.create_snapshot_from_providers(payload)

        self.assertIn("snapshot_id", result)
        self.assertIn("coverage", result)


if __name__ == "__main__":
    unittest.main()
