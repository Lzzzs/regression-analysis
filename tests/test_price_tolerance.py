"""Tests for backtest price gap tolerance."""
from datetime import date

from portfolio_lab.backtest import BacktestEngine
from portfolio_lab.models import CalendarType


class TestResolvePriceTolerance:
    def setup_method(self):
        self.engine = BacktestEngine(data_dir="/tmp/test_backtest_data")
        self.asset = {
            "identifier": "000001",
            "asset_type": "stock",
            "market": "CN",
            "calendar": "a_share",
            "quote_currency": "CNY",
        }

    def test_exact_match_returns_price(self):
        prices = {"2024-01-02": {"close": 10.0}}
        price, stale, closed = self.engine._resolve_asset_price(self.asset, prices, date(2024, 1, 2))
        assert price == 10.0
        assert stale is False

    def test_trading_day_gap_uses_lookback(self):
        """Monday 2024-01-08 is missing but Friday 2024-01-05 has data — should lookback."""
        prices = {"2024-01-05": {"close": 10.5}}
        price, stale, closed = self.engine._resolve_asset_price(self.asset, prices, date(2024, 1, 8))
        assert price == 10.5
        assert stale is True

    def test_trading_day_gap_within_10_days_uses_lookback(self):
        """National Day holiday: 8-day gap should still use lookback."""
        prices = {"2024-09-30": {"close": 10.0}}
        price, stale, closed = self.engine._resolve_asset_price(self.asset, prices, date(2024, 10, 8))
        assert price == 10.0
        assert stale is True

    def test_trading_day_gap_beyond_10_days_raises(self):
        """If no price within 10 lookback days, should raise."""
        prices = {"2023-12-15": {"close": 10.0}}  # too far back
        import pytest
        with pytest.raises(Exception, match="missing price"):
            self.engine._resolve_asset_price(self.asset, prices, date(2024, 1, 8))

    def test_weekend_uses_last_known(self):
        """Weekend should use last known price (existing behavior)."""
        prices = {"2024-01-05": {"close": 10.5}}
        price, stale, closed = self.engine._resolve_asset_price(self.asset, prices, date(2024, 1, 6))
        assert price == 10.5
        assert stale is True
        assert closed is True
