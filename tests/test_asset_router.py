"""Tests for asset_router: resolve_asset_meta and search endpoint."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for p in [str(ROOT), str(ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from apps.api.asset_router import resolve_asset_meta


class TestResolveAssetMeta(unittest.TestCase):
    def test_cn_stock(self):
        meta = resolve_asset_meta("000300", "cn")
        self.assertEqual(meta["identifier"], "000300")
        self.assertEqual(meta["asset_type"], "stock")
        self.assertEqual(meta["market"], "CN")
        self.assertEqual(meta["calendar"], "a_share")
        self.assertEqual(meta["quote_currency"], "CNY")

    def test_cn_etf_starts_with_5(self):
        meta = resolve_asset_meta("510300", "cn")
        self.assertEqual(meta["asset_type"], "etf")

    def test_cn_etf_starts_with_159(self):
        meta = resolve_asset_meta("159915", "cn")
        self.assertEqual(meta["asset_type"], "etf")

    def test_us_stock(self):
        meta = resolve_asset_meta("SPY", "us")
        self.assertEqual(meta["identifier"], "SPY")
        self.assertEqual(meta["asset_type"], "stock")
        self.assertEqual(meta["market"], "US")
        self.assertEqual(meta["calendar"], "us_equity")
        self.assertEqual(meta["quote_currency"], "USD")

    def test_hk_stock(self):
        meta = resolve_asset_meta("00700", "hk")
        self.assertEqual(meta["identifier"], "00700")
        self.assertEqual(meta["asset_type"], "stock")
        self.assertEqual(meta["market"], "HK")
        self.assertEqual(meta["calendar"], "hk_equity")
        self.assertEqual(meta["quote_currency"], "HKD")

    def test_crypto(self):
        meta = resolve_asset_meta("BTC", "crypto")
        self.assertEqual(meta["identifier"], "BTC")
        self.assertEqual(meta["asset_type"], "crypto")
        self.assertEqual(meta["market"], "CRYPTO")
        self.assertEqual(meta["calendar"], "crypto_7d")
        self.assertEqual(meta["quote_currency"], "USD")

    def test_unknown_market_raises(self):
        from portfolio_lab.errors import ValidationError
        with self.assertRaises(ValidationError):
            resolve_asset_meta("ABC", "unknown")


class TestSearchAssetsEndpoint(unittest.TestCase):
    def setUp(self):
        try:
            from fastapi.testclient import TestClient
            from apps.api.asset_router import router
            from fastapi import FastAPI
            app = FastAPI()
            app.include_router(router)
            self.client = TestClient(app)
            self.fastapi_available = True
        except ImportError:
            self.fastapi_available = False

    def test_search_cn_returns_items(self):
        if not self.fastapi_available:
            self.skipTest("fastapi not installed")
        mock_stocks = pd.DataFrame({
            "代码": ["000300", "000001"],
            "名称": ["沪深300指数", "平安银行"],
        })
        mock_etf = pd.DataFrame({
            "代码": ["510300", "159915"],
            "名称": ["沪深300ETF", "易方达创业板ETF"],
        })
        import apps.api.asset_router as ar
        ar._cn_cache["data"] = None
        ar._cn_cache["ts"] = 0.0
        with patch("apps.api.asset_router.ak") as mock_ak:
            mock_ak.stock_info_a_code_name.return_value = mock_stocks
            mock_ak.fund_etf_spot_em.return_value = mock_etf
            resp = self.client.get("/assets/search?market=cn&q=300")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("items", body)
        codes = [item["code"] for item in body["items"]]
        self.assertIn("000300", codes)
        self.assertIn("510300", codes)

    def test_search_crypto_returns_fixed_list(self):
        if not self.fastapi_available:
            self.skipTest("fastapi not installed")
        resp = self.client.get("/assets/search?market=crypto&q=")
        self.assertEqual(resp.status_code, 200)
        codes = [item["code"] for item in resp.json()["items"]]
        self.assertIn("BTC", codes)
        self.assertIn("ETH", codes)

    def test_missing_market_returns_422(self):
        if not self.fastapi_available:
            self.skipTest("fastapi not installed")
        resp = self.client.get("/assets/search?q=test")
        self.assertEqual(resp.status_code, 422)

    def test_invalid_market_returns_400(self):
        if not self.fastapi_available:
            self.skipTest("fastapi not installed")
        resp = self.client.get("/assets/search?market=xyz&q=test")
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
