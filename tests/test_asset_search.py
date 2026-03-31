"""Tests for asset search including ETFs and fallback."""
from unittest.mock import patch, MagicMock
import pandas as pd

from apps.api.asset_router import _fetch_cn_items, _FALLBACK_CN_ITEMS


class TestFetchCnItems:
    def test_includes_etfs_from_stock_list(self):
        """510300 starts with '5' so it should be tagged as ETF."""
        stock_df = pd.DataFrame({"code": ["000001", "510300"], "name": ["平安银行", "沪深300ETF"]})
        etf_df = pd.DataFrame({"代码": ["159915"], "名称": ["创业板ETF"]})

        with patch("apps.api.asset_router.ak") as mock_ak:
            mock_ak.stock_info_a_code_name.return_value = stock_df
            mock_ak.fund_etf_spot_em.return_value = etf_df
            items = _fetch_cn_items()

        codes = [item["code"] for item in items]
        assert "510300" in codes
        assert "159915" in codes
        assert "000001" in codes

    def test_search_filters_by_code(self):
        """Searching '510300' should find it in the list."""
        stock_df = pd.DataFrame({"code": ["000001", "510300"], "name": ["平安银行", "沪深300ETF"]})
        etf_df = pd.DataFrame({"代码": ["159915"], "名称": ["创业板ETF"]})

        with patch("apps.api.asset_router.ak") as mock_ak:
            mock_ak.stock_info_a_code_name.return_value = stock_df
            mock_ak.fund_etf_spot_em.return_value = etf_df
            items = _fetch_cn_items()

        q = "510300"
        filtered = [i for i in items if q in i["code"].lower() or q in i["name"].lower()]
        assert len(filtered) == 1
        assert filtered[0]["code"] == "510300"

    def test_fallback_when_akshare_unavailable(self):
        """When ak is None, should return fallback list."""
        with patch("apps.api.asset_router.ak", None):
            items = _fetch_cn_items()

        assert len(items) > 0
        codes = [i["code"] for i in items]
        assert "510300" in codes  # CSI300 ETF must be in fallback


class TestFallbackList:
    def test_fallback_has_common_assets(self):
        assert any(i["code"] == "510300" for i in _FALLBACK_CN_ITEMS)
        assert any(i["code"] == "000001" for i in _FALLBACK_CN_ITEMS)
