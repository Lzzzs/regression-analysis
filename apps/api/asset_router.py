"""Asset search API router with in-memory 5-minute cache."""
from __future__ import annotations

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
_CACHE_TTL = 300  # 5 minutes

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
        return []
    df = ak.stock_us_spot_em()
    code_col = _col(df, "代码", "code")
    name_col = _col(df, "名称", "name")
    items: list[dict] = []
    for _, row in df.iterrows():
        items.append({"code": str(row[code_col]).strip(), "name": str(row[name_col]).strip(), "market": "us", "asset_type": "stock"})
    return items


def _fetch_hk_items() -> list[dict]:
    if ak is None:
        return []
    df = ak.stock_hk_spot_em()
    code_col = _col(df, "代码", "code")
    name_col = _col(df, "名称", "name")
    items: list[dict] = []
    for _, row in df.iterrows():
        items.append({"code": str(row[code_col]).strip(), "name": str(row[name_col]).strip(), "market": "hk", "asset_type": "stock"})
    return items


def _get_cached_items(market: str) -> list[dict]:
    if market == "cn":
        if _is_stale(_cn_cache):
            _cn_cache["data"] = _fetch_cn_items()
            _cn_cache["ts"] = time.time()
        return _cn_cache["data"]
    elif market == "us":
        if _is_stale(_us_cache):
            _us_cache["data"] = _fetch_us_items()
            _us_cache["ts"] = time.time()
        return _us_cache["data"]
    elif market == "hk":
        if _is_stale(_hk_cache):
            _hk_cache["data"] = _fetch_hk_items()
            _hk_cache["ts"] = time.time()
        return _hk_cache["data"]
    elif market == "crypto":
        return _CRYPTO_ITEMS
    return []


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
