"""Core domain models and schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

from .errors import ValidationError


class AssetType(str, Enum):
    INDEX = "index"
    ETF = "etf"
    STOCK = "stock"
    BOND = "bond"
    COMMODITY = "commodity"
    CRYPTO = "crypto"
    CASH = "cash"


class CalendarType(str, Enum):
    A_SHARE = "a_share"
    US_EQUITY = "us_equity"
    CRYPTO_7D = "crypto_7d"


class RebalanceFrequency(str, Enum):
    NONE = "none"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class MissingDataPolicy(str, Enum):
    FAIL_FAST = "fail_fast"


@dataclass(slots=True)
class AssetDefinition:
    identifier: str
    asset_type: AssetType
    market: str
    calendar: CalendarType
    quote_currency: str
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.identifier or not self.identifier.strip():
            raise ValidationError("asset identifier is required")
        self.identifier = self.identifier.strip().upper()
        self.market = self.market.strip().upper()
        self.quote_currency = self.quote_currency.strip().upper()
        if len(self.quote_currency) != 3:
            raise ValidationError("quote currency must be 3-letter code")


@dataclass(slots=True)
class PricePoint:
    asset_id: str
    day: date
    close: float
    source: str

    def __post_init__(self) -> None:
        if self.close <= 0:
            raise ValidationError("close must be positive")
        if not self.source:
            raise ValidationError("source is required")
        self.asset_id = self.asset_id.upper()


@dataclass(slots=True)
class FXPoint:
    pair: str
    day: date
    rate: float
    source: str

    def __post_init__(self) -> None:
        if self.rate <= 0:
            raise ValidationError("fx rate must be positive")
        pair = self.pair.upper()
        if "/" not in pair:
            raise ValidationError("fx pair must be BASE/QUOTE format")
        self.pair = pair
        if not self.source:
            raise ValidationError("source is required")


@dataclass(slots=True)
class UniverseSpec:
    asset_ids: list[str]

    def __post_init__(self) -> None:
        if not self.asset_ids:
            raise ValidationError("universe asset_ids cannot be empty")
        self.asset_ids = [a.upper() for a in self.asset_ids]


@dataclass(slots=True)
class PortfolioSpec:
    weights: dict[str, float]
    base_currency: str = "CNY"
    tolerance: float = 1e-6

    def __post_init__(self) -> None:
        if not self.weights:
            raise ValidationError("portfolio weights cannot be empty")
        self.weights = {k.upper(): float(v) for k, v in self.weights.items()}
        self.base_currency = self.base_currency.upper()


@dataclass(slots=True)
class BacktestSpec:
    snapshot_id: str
    start_date: date
    end_date: date
    rebalance_frequency: RebalanceFrequency
    base_currency: str = "CNY"
    transaction_cost_bps: float = 0.0
    slippage_bps: float = 0.0
    missing_data_policy: MissingDataPolicy = MissingDataPolicy.FAIL_FAST

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            raise ValidationError("snapshot_id is required")
        if self.start_date > self.end_date:
            raise ValidationError("start_date must be <= end_date")
        self.base_currency = self.base_currency.upper()
        if self.transaction_cost_bps < 0 or self.slippage_bps < 0:
            raise ValidationError("cost bps cannot be negative")


@dataclass(slots=True)
class ExperimentRunMetadata:
    run_id: str
    snapshot_id: str
    created_at: datetime
    input_hash: str
    data_version: str
    engine_version: str
    assumptions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EquityPoint:
    day: date
    equity: float
    cash: float
    stale_assets: list[str] = field(default_factory=list)
    no_trade_assets: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SingleRunResult:
    run_id: str
    portfolio_id: str
    metadata: ExperimentRunMetadata
    equity_curve: list[EquityPoint]
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class BatchRunResult:
    objective: str
    runs: list[SingleRunResult]
    ranking: list[dict[str, Any]]


def to_primitive(value: Any) -> Any:
    """Convert dataclass-heavy structures to JSON-serializable primitives."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {k: to_primitive(getattr(value, k)) for k in value.__dataclass_fields__}
    if isinstance(value, dict):
        return {str(k): to_primitive(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_primitive(v) for v in value]
    return value
