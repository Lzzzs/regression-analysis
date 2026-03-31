"""Asset search API router with in-memory 5-minute cache."""
from __future__ import annotations

import threading
import time
from typing import Any

from portfolio_lab.errors import ValidationError

try:
    import akshare as ak
except ImportError:
    ak = None  # type: ignore[assignment]

try:
    from fastapi import APIRouter, HTTPException, Query
    router = APIRouter()
    _FASTAPI_AVAILABLE = True
except ImportError:
    router = None  # type: ignore[assignment]
    _FASTAPI_AVAILABLE = False

# ---------------------------------------------------------------------------
# In-memory caches — one per market, each entry: {"data": list, "ts": float}
# ---------------------------------------------------------------------------
_CACHE_TTL = 1800  # 30 minutes — akshare calls are slow, cache aggressively
_REFRESH_LOCK = threading.Lock()

_cn_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_us_cache: dict[str, Any] = {"data": None, "ts": 0.0}
_hk_cache: dict[str, Any] = {"data": None, "ts": 0.0}

_CRYPTO_ITEMS = [
    {"code": "BTC", "name": "Bitcoin", "market": "crypto", "asset_type": "crypto"},
    {"code": "ETH", "name": "Ethereum", "market": "crypto", "asset_type": "crypto"},
    {"code": "SOL", "name": "Solana", "market": "crypto", "asset_type": "crypto"},
    {"code": "BNB", "name": "BNB", "market": "crypto", "asset_type": "crypto"},
    {"code": "XRP", "name": "XRP", "market": "crypto", "asset_type": "crypto"},
]

_FALLBACK_CN_ITEMS: list[dict] = [
    {"code": "000001", "name": "平安银行", "market": "cn", "asset_type": "stock"},
    {"code": "000002", "name": "万科A", "market": "cn", "asset_type": "stock"},
    {"code": "000300", "name": "沪深300", "market": "cn", "asset_type": "index"},
    {"code": "600519", "name": "贵州茅台", "market": "cn", "asset_type": "stock"},
    {"code": "601318", "name": "中国平安", "market": "cn", "asset_type": "stock"},
    {"code": "600036", "name": "招商银行", "market": "cn", "asset_type": "stock"},
    {"code": "000858", "name": "五粮液", "market": "cn", "asset_type": "stock"},
    {"code": "601012", "name": "隆基绿能", "market": "cn", "asset_type": "stock"},
    {"code": "600900", "name": "长江电力", "market": "cn", "asset_type": "stock"},
    {"code": "601888", "name": "中国中免", "market": "cn", "asset_type": "stock"},
    {"code": "510300", "name": "沪深300ETF", "market": "cn", "asset_type": "etf"},
    {"code": "510500", "name": "中证500ETF", "market": "cn", "asset_type": "etf"},
    {"code": "510050", "name": "上证50ETF", "market": "cn", "asset_type": "etf"},
    {"code": "159919", "name": "沪深300ETF", "market": "cn", "asset_type": "etf"},
    {"code": "159915", "name": "创业板ETF", "market": "cn", "asset_type": "etf"},
    {"code": "513100", "name": "纳指ETF", "market": "cn", "asset_type": "etf"},
    {"code": "518880", "name": "黄金ETF", "market": "cn", "asset_type": "etf"},
    {"code": "511010", "name": "国债ETF", "market": "cn", "asset_type": "etf"},
    {"code": "513050", "name": "中概互联ETF", "market": "cn", "asset_type": "etf"},
    {"code": "512690", "name": "酒ETF", "market": "cn", "asset_type": "etf"},
]

_FALLBACK_US_ITEMS: list[dict] = [
    {"code": "AAPL", "name": "Apple", "market": "us", "asset_type": "stock"},
    {"code": "MSFT", "name": "Microsoft", "market": "us", "asset_type": "stock"},
    {"code": "GOOGL", "name": "Alphabet", "market": "us", "asset_type": "stock"},
    {"code": "AMZN", "name": "Amazon", "market": "us", "asset_type": "stock"},
    {"code": "NVDA", "name": "NVIDIA", "market": "us", "asset_type": "stock"},
    {"code": "TSLA", "name": "Tesla", "market": "us", "asset_type": "stock"},
    {"code": "META", "name": "Meta Platforms", "market": "us", "asset_type": "stock"},
    {"code": "BRK.B", "name": "Berkshire Hathaway B", "market": "us", "asset_type": "stock"},
    {"code": "JPM", "name": "JPMorgan Chase", "market": "us", "asset_type": "stock"},
    {"code": "V", "name": "Visa", "market": "us", "asset_type": "stock"},
    {"code": "SPY", "name": "S&P 500 ETF", "market": "us", "asset_type": "etf"},
    {"code": "QQQ", "name": "Nasdaq 100 ETF", "market": "us", "asset_type": "etf"},
    {"code": "IWM", "name": "Russell 2000 ETF", "market": "us", "asset_type": "etf"},
    {"code": "TLT", "name": "20+ Year Treasury ETF", "market": "us", "asset_type": "etf"},
    {"code": "GLD", "name": "Gold ETF", "market": "us", "asset_type": "etf"},
]

_FALLBACK_HK_ITEMS: list[dict] = [
    {"code": "00700", "name": "腾讯控股", "market": "hk", "asset_type": "stock"},
    {"code": "09988", "name": "阿里巴巴-W", "market": "hk", "asset_type": "stock"},
    {"code": "03690", "name": "美团-W", "market": "hk", "asset_type": "stock"},
    {"code": "09999", "name": "网易-S", "market": "hk", "asset_type": "stock"},
    {"code": "01810", "name": "小米集团-W", "market": "hk", "asset_type": "stock"},
    {"code": "09618", "name": "京东集团-SW", "market": "hk", "asset_type": "stock"},
    {"code": "00941", "name": "中国移动", "market": "hk", "asset_type": "stock"},
    {"code": "02318", "name": "中国平安", "market": "hk", "asset_type": "stock"},
    {"code": "00005", "name": "汇丰控股", "market": "hk", "asset_type": "stock"},
    {"code": "01211", "name": "比亚迪股份", "market": "hk", "asset_type": "stock"},
    {"code": "02800", "name": "盈富基金", "market": "hk", "asset_type": "etf"},
    {"code": "03067", "name": "安硕恒生科技ETF", "market": "hk", "asset_type": "etf"},
]


def resolve_asset_meta(code: str, market: str) -> dict:
    """Return asset metadata inferred from code and market.

    market: 'cn' | 'us' | 'hk' | 'crypto' (case-insensitive)
    Returns: {identifier, asset_type, market, calendar, quote_currency}
    """
    market_lower = market.lower()
    code_upper = code.upper()

    if market_lower == "cn":
        # Shanghai ETFs: 51xxxx; Shenzhen ETFs: 159xxx.
        # A-share stocks use 0/3/6 prefix — no false positives in practice.
        if code_upper.startswith("5") or code_upper.startswith("159"):
            asset_type = "etf"
        else:
            asset_type = "stock"
        return {
            "identifier": code_upper,
            "asset_type": asset_type,
            "market": "CN",
            "calendar": "a_share",
            "quote_currency": "CNY",
        }
    elif market_lower == "us":
        return {
            "identifier": code_upper,
            "asset_type": "stock",
            "market": "US",
            "calendar": "us_equity",
            "quote_currency": "USD",
        }
    elif market_lower == "hk":
        return {
            "identifier": code_upper,
            "asset_type": "stock",
            "market": "HK",
            "calendar": "hk_equity",
            "quote_currency": "HKD",
        }
    elif market_lower == "crypto":
        return {
            "identifier": code_upper,
            "asset_type": "crypto",
            "market": "CRYPTO",
            "calendar": "crypto_7d",
            "quote_currency": "USD",
        }
    else:
        raise ValidationError(f"unsupported market: {market}")


def _is_stale(cache: dict) -> bool:
    return cache["data"] is None or (time.time() - cache["ts"]) > _CACHE_TTL


def _col(df: Any, *candidates: str) -> str:
    """Find the first matching column name from candidates."""
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"none of {candidates} found in columns {df.columns.tolist()}")


def _fetch_cn_items() -> list[dict]:
    if ak is None:
        return list(_FALLBACK_CN_ITEMS)
    try:
        stocks_df = ak.stock_info_a_code_name()
        code_col = _col(stocks_df, "code", "代码")
        name_col = _col(stocks_df, "name", "名称")
        items: list[dict] = []
        for _, row in stocks_df.iterrows():
            code = str(row[code_col]).strip()
            # Shanghai ETFs: 51xxxx; Shenzhen ETFs: 159xxx
            asset_type = "etf" if (code.startswith("5") or code.startswith("159")) else "stock"
            items.append({"code": code, "name": str(row[name_col]).strip(), "market": "cn", "asset_type": asset_type})
        # Try to supplement with dedicated ETF list (may fail due to network)
        try:
            etf_df = ak.fund_etf_spot_em()
            etf_code_col = _col(etf_df, "代码", "code")
            etf_name_col = _col(etf_df, "名称", "name")
            existing_codes = {item["code"] for item in items}
            for _, row in etf_df.iterrows():
                code = str(row[etf_code_col]).strip()
                if code not in existing_codes:
                    items.append({"code": code, "name": str(row[etf_name_col]).strip(), "market": "cn", "asset_type": "etf"})
        except Exception:
            pass  # ETF supplement failed, stock list still available
        return items
    except Exception:
        return list(_FALLBACK_CN_ITEMS)


def _fetch_us_items() -> list[dict]:
    if ak is None:
        return list(_FALLBACK_US_ITEMS)
    try:
        df = ak.stock_us_spot_em()
        code_col = _col(df, "代码", "code")
        name_col = _col(df, "名称", "name")
        items: list[dict] = []
        for _, row in df.iterrows():
            items.append({"code": str(row[code_col]).strip(), "name": str(row[name_col]).strip(), "market": "us", "asset_type": "stock"})
        return items
    except Exception:
        return list(_FALLBACK_US_ITEMS)


def _fetch_hk_items() -> list[dict]:
    if ak is None:
        return list(_FALLBACK_HK_ITEMS)
    try:
        df = ak.stock_hk_spot_em()
        code_col = _col(df, "代码", "code")
        name_col = _col(df, "名称", "name")
        items: list[dict] = []
        for _, row in df.iterrows():
            items.append({"code": str(row[code_col]).strip(), "name": str(row[name_col]).strip(), "market": "hk", "asset_type": "stock"})
        return items
    except Exception:
        return list(_FALLBACK_HK_ITEMS)


_FALLBACK_MAP = {
    "cn": _FALLBACK_CN_ITEMS,
    "us": _FALLBACK_US_ITEMS,
    "hk": _FALLBACK_HK_ITEMS,
}

_CACHE_MAP = {
    "cn": _cn_cache,
    "us": _us_cache,
    "hk": _hk_cache,
}

_FETCH_MAP = {
    "cn": _fetch_cn_items,
    "us": _fetch_us_items,
    "hk": _fetch_hk_items,
}


def _refresh_cache_background(market: str) -> None:
    """Refresh cache in a background thread — never blocks the request."""
    if not _REFRESH_LOCK.acquire(blocking=False):
        return  # another refresh already in progress
    try:
        fetch_fn = _FETCH_MAP.get(market)
        cache = _CACHE_MAP.get(market)
        if fetch_fn and cache:
            data = fetch_fn()
            if data:
                cache["data"] = data
                cache["ts"] = time.time()
    except Exception:
        pass
    finally:
        _REFRESH_LOCK.release()


def _get_cached_items(market: str) -> list[dict]:
    if market == "crypto":
        return _CRYPTO_ITEMS

    cache = _CACHE_MAP.get(market)
    fallback = _FALLBACK_MAP.get(market, [])
    if cache is None:
        return list(fallback)

    if cache["data"] is not None:
        # Have cached data — return it immediately, refresh in background if stale
        if _is_stale(cache):
            threading.Thread(target=_refresh_cache_background, args=(market,), daemon=True).start()
        return cache["data"]

    # No cached data yet — return fallback immediately, trigger background fetch
    threading.Thread(target=_refresh_cache_background, args=(market,), daemon=True).start()
    return list(fallback)


if _FASTAPI_AVAILABLE:
    @router.get("/assets/search")
    def search_assets(
        market: str = Query(..., description="cn | us | hk | crypto"),
        q: str = Query("", description="search query (code or name)"),
        limit: int = Query(30, ge=1, le=100),
    ) -> dict:
        market_lower = market.lower()
        if market_lower not in ("cn", "us", "hk", "crypto"):
            raise HTTPException(status_code=400, detail=f"unsupported market: {market}")

        try:
            all_items = _get_cached_items(market_lower)
        except Exception:
            all_items = []
        q_lower = q.strip().lower()
        if q_lower:
            filtered = [
                item for item in all_items
                if q_lower in item["code"].lower() or q_lower in item["name"].lower()
            ]
        else:
            filtered = all_items

        return {"items": filtered[:limit]}
