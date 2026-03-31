"""Tests for AKShare-backed data providers."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for p in [str(ROOT), str(ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from portfolio_lab.data_adapters import AKShareFXProvider, AKSharePriceProvider


class TestAKSharePriceProviderCNStock(unittest.TestCase):
    def test_fetches_cn_stock_rows(self):
        """CN stock uses stock_zh_a_daily (Sina) as primary source."""
        mock_df = pd.DataFrame({
            "date": ["2026-01-05", "2026-01-06", "2026-01-09"],
            "close": [4000.0, 4010.0, 4020.0],
        })
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.stock_zh_a_daily.return_value = mock_df
            provider = AKSharePriceProvider(market="cn")
            rows = provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "000300")

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["day"], date(2026, 1, 5))
        self.assertAlmostEqual(rows[0]["close"], 4000.0)
        self.assertEqual(rows[0]["source"], "akshare")
        mock_ak.stock_zh_a_daily.assert_called_once_with(
            symbol="sz000300",
            start_date="20260105",
            end_date="20260109",
            adjust="qfq",
        )

    def test_fetches_cn_etf_rows(self):
        """CN ETF uses fund_etf_hist_sina as primary source."""
        mock_df = pd.DataFrame({
            "date": ["2026-01-05"],
            "close": [3.5],
        })
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.fund_etf_hist_sina.return_value = mock_df
            provider = AKSharePriceProvider(market="cn")
            # 510300 starts with '5' → ETF branch
            rows = provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "510300")

        self.assertEqual(len(rows), 1)
        mock_ak.fund_etf_hist_sina.assert_called_once_with(symbol="sh510300")

    def test_fetches_cn_etf_159_prefix(self):
        """159xxx ETFs use sz prefix for Sina."""
        mock_df = pd.DataFrame({"date": ["2026-01-05"], "close": [2.0]})
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.fund_etf_hist_sina.return_value = mock_df
            provider = AKSharePriceProvider(market="cn")
            provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "159915")
        mock_ak.fund_etf_hist_sina.assert_called_once_with(symbol="sz159915")


class TestAKSharePriceProviderUS(unittest.TestCase):
    def test_fetches_us_stock_rows(self):
        mock_df = pd.DataFrame({
            "日期": ["2026-01-05", "2026-01-06"],
            "收盘": [500.0, 505.0],
        })
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.stock_us_hist.return_value = mock_df
            provider = AKSharePriceProvider(market="us")
            rows = provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "SPY")

        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[1]["close"], 505.0)
        mock_ak.stock_us_hist.assert_called_once_with(
            symbol="SPY",
            period="daily",
            start_date="20260105",
            end_date="20260109",
            adjust="qfq",
        )


class TestAKSharePriceProviderHK(unittest.TestCase):
    def test_fetches_hk_stock_rows(self):
        mock_df = pd.DataFrame({"日期": ["2026-01-05"], "收盘": [350.0]})
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.stock_hk_hist.return_value = mock_df
            provider = AKSharePriceProvider(market="hk")
            rows = provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "00700")

        self.assertEqual(len(rows), 1)
        mock_ak.stock_hk_hist.assert_called_once_with(
            symbol="00700",
            period="daily",
            start_date="20260105",
            end_date="20260109",
            adjust="qfq",
        )


class TestAKSharePriceProviderCrypto(unittest.TestCase):
    def test_crypto_raises_validation_error(self):
        """Crypto market should no longer use AKSharePriceProvider — it raises ValidationError."""
        from portfolio_lab.errors import ValidationError
        provider = AKSharePriceProvider(market="crypto")
        with self.assertRaises(ValidationError):
            provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "BTC")


class TestAKShareFXProvider(unittest.TestCase):
    def test_fetches_usd_cny(self):
        mock_df = pd.DataFrame({
            "日期": ["2026-01-05", "2026-01-06"],
            "央行中间价": [725.0, 726.0],
            "中行折算价": [725.0, 726.0],
        })
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.currency_boc_sina.return_value = mock_df
            provider = AKShareFXProvider()
            rows = provider.fetch_fx_rows(date(2026, 1, 5), date(2026, 1, 9), "USD/CNY")

        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0]["rate"], 7.25)
        self.assertEqual(rows[0]["day"], date(2026, 1, 5))
        self.assertEqual(rows[0]["source"], "akshare")
        mock_ak.currency_boc_sina.assert_called_once_with(
            symbol="美元",
            start_date="20260105",
            end_date="20260109",
        )

    def test_fetches_hkd_cny(self):
        mock_df = pd.DataFrame({
            "日期": ["2026-01-05"],
            "央行中间价": [93.0],
            "中行折算价": [93.0],
        })
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.currency_boc_sina.return_value = mock_df
            provider = AKShareFXProvider()
            rows = provider.fetch_fx_rows(date(2026, 1, 5), date(2026, 1, 9), "HKD/CNY")

        mock_ak.currency_boc_sina.assert_called_once_with(
            symbol="港币",
            start_date="20260105",
            end_date="20260109",
        )

    def test_falls_back_to_折算价_when_央行中间价_is_nan(self):
        mock_df = pd.DataFrame({
            "日期": ["2026-01-05"],
            "央行中间价": [float("nan")],
            "中行折算价": [718.84],
        })
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.currency_boc_sina.return_value = mock_df
            provider = AKShareFXProvider()
            rows = provider.fetch_fx_rows(date(2026, 1, 5), date(2026, 1, 9), "USD/CNY")

        self.assertAlmostEqual(rows[0]["rate"], 7.1884)


class TestAKShareErrorPaths(unittest.TestCase):
    def test_price_provider_invalid_market_raises_validation_error(self):
        from portfolio_lab.errors import ValidationError
        with patch("portfolio_lab.data_adapters.ak"):
            provider = AKSharePriceProvider(market="xyz")
            with self.assertRaises(ValidationError):
                provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "ABC")

    def test_fx_provider_unsupported_pair_raises_validation_error(self):
        from portfolio_lab.errors import ValidationError
        with patch("portfolio_lab.data_adapters.ak"):
            provider = AKShareFXProvider()
            with self.assertRaises(ValidationError):
                provider.fetch_fx_rows(date(2026, 1, 5), date(2026, 1, 9), "EUR/USD")

    def test_price_provider_raises_import_error_when_ak_none(self):
        import portfolio_lab.data_adapters as da
        original_ak = da.ak
        try:
            da.ak = None
            provider = AKSharePriceProvider(market="cn")
            with self.assertRaises(ImportError):
                provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "000300")
        finally:
            da.ak = original_ak

    def test_fx_provider_raises_import_error_when_ak_none(self):
        import portfolio_lab.data_adapters as da
        original_ak = da.ak
        try:
            da.ak = None
            provider = AKShareFXProvider()
            with self.assertRaises(ImportError):
                provider.fetch_fx_rows(date(2026, 1, 5), date(2026, 1, 9), "USD/CNY")
        finally:
            da.ak = original_ak


if __name__ == "__main__":
    unittest.main()
