"""Tests for AKShare-backed data providers."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for p in [str(ROOT), str(ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from portfolio_lab.data_adapters import AKShareFXProvider, AKSharePriceProvider


class TestAKSharePriceProviderCNStock(unittest.TestCase):
    def test_fetches_cn_stock_rows(self):
        mock_df = pd.DataFrame({
            "日期": ["2026-01-05", "2026-01-06", "2026-01-09"],
            "收盘": [4000.0, 4010.0, 4020.0],
        })
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.stock_zh_a_hist.return_value = mock_df
            provider = AKSharePriceProvider(market="cn")
            rows = provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "000300")

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["day"], date(2026, 1, 5))
        self.assertAlmostEqual(rows[0]["close"], 4000.0)
        self.assertEqual(rows[0]["source"], "akshare")
        mock_ak.stock_zh_a_hist.assert_called_once_with(
            symbol="000300",
            period="daily",
            start_date="20260105",
            end_date="20260109",
            adjust="qfq",
        )

    def test_fetches_cn_etf_rows(self):
        mock_df = pd.DataFrame({
            "日期": ["2026-01-05"],
            "收盘": [3.5],
        })
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.fund_etf_hist_em.return_value = mock_df
            provider = AKSharePriceProvider(market="cn")
            # 510300 starts with '5' → ETF branch
            rows = provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "510300")

        self.assertEqual(len(rows), 1)
        mock_ak.fund_etf_hist_em.assert_called_once_with(
            symbol="510300",
            period="daily",
            start_date="20260105",
            end_date="20260109",
            adjust="qfq",
        )

    def test_fetches_cn_etf_159_prefix(self):
        mock_df = pd.DataFrame({"日期": ["2026-01-05"], "收盘": [2.0]})
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.fund_etf_hist_em.return_value = mock_df
            provider = AKSharePriceProvider(market="cn")
            provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "159915")
        mock_ak.fund_etf_hist_em.assert_called_once()


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
    def test_fetches_crypto_rows_appends_usdt(self):
        mock_df = pd.DataFrame({"日期": ["2026-01-05"], "收盘": [95000.0]})
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.crypto_hist.return_value = mock_df
            provider = AKSharePriceProvider(market="crypto")
            rows = provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "BTC")

        self.assertEqual(len(rows), 1)
        # BTC → BTCUSDT
        mock_ak.crypto_hist.assert_called_once_with(
            symbol="BTCUSDT",
            period="daily",
            start_date="20260105",
            end_date="20260109",
        )

    def test_does_not_double_append_usdt(self):
        mock_df = pd.DataFrame({"日期": ["2026-01-05"], "收盘": [95000.0]})
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.crypto_hist.return_value = mock_df
            provider = AKSharePriceProvider(market="crypto")
            provider.fetch_price_rows(date(2026, 1, 5), date(2026, 1, 9), "BTCUSDT")
        mock_ak.crypto_hist.assert_called_once_with(
            symbol="BTCUSDT",
            period="daily",
            start_date="20260105",
            end_date="20260109",
        )


class TestAKShareFXProvider(unittest.TestCase):
    def test_fetches_usd_cny(self):
        mock_df = pd.DataFrame({"日期": ["2026-01-05", "2026-01-06"], "收盘": [7.25, 7.26]})
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.currency_hist.return_value = mock_df
            provider = AKShareFXProvider()
            rows = provider.fetch_fx_rows(date(2026, 1, 5), date(2026, 1, 9), "USD/CNY")

        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0]["rate"], 7.25)
        self.assertEqual(rows[0]["day"], date(2026, 1, 5))
        self.assertEqual(rows[0]["source"], "akshare")
        mock_ak.currency_hist.assert_called_once_with(
            symbol="USDCNY",
            period="daily",
            start_date="20260105",
            end_date="20260109",
        )

    def test_fetches_hkd_cny(self):
        mock_df = pd.DataFrame({"日期": ["2026-01-05"], "收盘": [0.93]})
        with patch("portfolio_lab.data_adapters.ak") as mock_ak:
            mock_ak.currency_hist.return_value = mock_df
            provider = AKShareFXProvider()
            rows = provider.fetch_fx_rows(date(2026, 1, 5), date(2026, 1, 9), "HKD/CNY")

        mock_ak.currency_hist.assert_called_once_with(
            symbol="HKDCNY",
            period="daily",
            start_date="20260105",
            end_date="20260109",
        )


if __name__ == "__main__":
    unittest.main()
