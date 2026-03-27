"""Portfolio Lab core package."""

from .analysis import analyze_run, compare_across_windows, rank_batch
from .backtest import BacktestEngine
from .construction import (
    PortfolioGenerationConstraints,
    deterministic_portfolio_id,
    generate_portfolios,
    validate_fixed_weight_portfolio,
)
from .data_adapters import (
    FXDataProvider,
    LocalCSVFXProvider,
    LocalCSVPriceProvider,
    LocalJSONMarketDataAdapter,
    MarketDataAdapter,
    PriceDataProvider,
    RoutedMarketDataAdapter,
)
from .models import (
    AssetDefinition,
    AssetType,
    BacktestSpec,
    CalendarType,
    ExperimentRunMetadata,
    FXPoint,
    MissingDataPolicy,
    PortfolioSpec,
    PricePoint,
    RebalanceFrequency,
    SingleRunResult,
)
from .universe import UniverseStore

__all__ = [
    "AssetDefinition",
    "AssetType",
    "BacktestEngine",
    "BacktestSpec",
    "CalendarType",
    "ExperimentRunMetadata",
    "FXPoint",
    "FXDataProvider",
    "LocalCSVFXProvider",
    "LocalCSVPriceProvider",
    "LocalJSONMarketDataAdapter",
    "MarketDataAdapter",
    "MissingDataPolicy",
    "PortfolioGenerationConstraints",
    "PortfolioSpec",
    "PricePoint",
    "PriceDataProvider",
    "RebalanceFrequency",
    "RoutedMarketDataAdapter",
    "SingleRunResult",
    "UniverseStore",
    "analyze_run",
    "compare_across_windows",
    "deterministic_portfolio_id",
    "generate_portfolios",
    "rank_batch",
    "validate_fixed_weight_portfolio",
]
