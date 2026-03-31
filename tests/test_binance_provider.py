"""Tests for BinancePriceProvider."""
from datetime import date
from unittest.mock import patch, MagicMock
import json

from portfolio_lab.data_adapters import BinancePriceProvider


def _mock_klines_response(days: int = 3, start_price: float = 30000.0):
    """Build a fake Binance klines JSON response."""
    base_ts = 1704067200000  # 2024-01-01 00:00 UTC
    day_ms = 86400000
    return [
        [
            base_ts + i * day_ms,   # open time
            str(start_price + i),   # open
            str(start_price + i + 100),  # high
            str(start_price + i - 100),  # low
            str(start_price + i * 10),   # close
            "100.0",                # volume
            base_ts + (i + 1) * day_ms - 1,  # close time
            "3000000", 100, "50.0", "1500000", "0",
        ]
        for i in range(days)
    ]


class TestBinancePriceProvider:
    def test_fetch_maps_symbol_and_returns_rows(self):
        provider = BinancePriceProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _mock_klines_response(3)

        with patch("portfolio_lab.data_adapters._requests.get", return_value=mock_resp) as mock_get:
            rows = provider.fetch_price_rows(date(2024, 1, 1), date(2024, 1, 3), "BTC")

        assert len(rows) == 3
        assert rows[0]["source"] == "binance"
        assert rows[0]["close"] == 30000.0  # first close = 30000 + 0*10
        assert isinstance(rows[0]["day"], date)
        # Verify symbol mapping: BTC -> BTCUSDT
        call_kwargs = mock_get.call_args
        call_params = call_kwargs[1]["params"] if "params" in call_kwargs[1] else call_kwargs[0][1]
        assert call_params["symbol"] == "BTCUSDT"

    def test_fetch_symbol_already_has_usdt_suffix(self):
        provider = BinancePriceProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _mock_klines_response(1)

        with patch("portfolio_lab.data_adapters._requests.get", return_value=mock_resp) as mock_get:
            rows = provider.fetch_price_rows(date(2024, 1, 1), date(2024, 1, 1), "BTCUSDT")

        call_kwargs = mock_get.call_args
        call_params = call_kwargs[1]["params"] if "params" in call_kwargs[1] else call_kwargs[0][1]
        assert call_params["symbol"] == "BTCUSDT"
        # Ensure no double USDT
        assert "BTCUSDTUSDT" not in str(call_params)

    def test_fetch_falls_back_to_csv_on_api_failure(self):
        provider = BinancePriceProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("portfolio_lab.data_adapters._requests.get", return_value=mock_resp):
            with patch.object(provider, "_fallback_csv") as mock_csv:
                mock_csv.return_value = [{"day": date(2024, 1, 1), "close": 42000.0, "source": "crypto-csv"}]
                rows = provider.fetch_price_rows(date(2024, 1, 1), date(2024, 1, 1), "BTC")

        assert len(rows) == 1
        assert rows[0]["source"] == "crypto-csv"

    def test_fetch_falls_back_on_network_error(self):
        provider = BinancePriceProvider()

        with patch("portfolio_lab.data_adapters._requests.get", side_effect=Exception("timeout")):
            with patch.object(provider, "_fallback_csv") as mock_csv:
                mock_csv.return_value = []
                rows = provider.fetch_price_rows(date(2024, 1, 1), date(2024, 1, 1), "BTC")

        assert rows == []
