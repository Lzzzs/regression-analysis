## 1. Domain Models And Interfaces

- [x] 1.1 Define `UniverseSpec`, `PortfolioSpec`, `BacktestSpec`, and experiment run metadata schemas.
- [x] 1.2 Define normalized asset price and FX series interfaces with validation rules.
- [x] 1.3 Define canonical result schema for single run and batch run outputs.

## 2. Universe Module

- [x] 2.1 Implement asset registration with required metadata validation (market, currency, calendar, type).
- [x] 2.2 Implement normalized daily price ingestion with row-level validation errors.
- [x] 2.3 Implement daily incremental ingestion and weekly frozen snapshot publishing workflow.
- [x] 2.4 Implement snapshot quality gates for expected-trading-day completeness and traceability.
- [x] 2.5 Implement universe query API that exposes calendar and currency metadata for selected assets.

## 3. Portfolio Construction Module

- [x] 3.1 Implement fixed-weight portfolio validation with total-weight tolerance checks.
- [x] 3.2 Implement constraint-based candidate generation (per-asset cap, group cap, cash floor).
- [x] 3.3 Implement deterministic portfolio identifier generation from normalized composition.

## 4. Backtest Engine

- [x] 4.1 Implement date-range execution with configurable rebalance frequency (none/monthly/quarterly) bound to `snapshot_id`.
- [x] 4.2 Implement cost-aware rebalance accounting with transaction cost and slippage hooks.
- [x] 4.3 Implement base-currency valuation with FX conversion and missing-FX policy handling.
- [x] 4.4 Enforce no outbound market-data API calls during backtest execution.
- [x] 4.5 Persist reproducibility metadata (input specs, `snapshot_id`, data versions, execution timestamp) per run.
- [x] 4.6 Enforce accuracy-first missing data policy (fail-fast on expected-trading-day gaps, no forward-fill interpolation).
- [x] 4.7 Implement market-closed-day stale valuation marking and no-trade behavior for closed assets.

## 5. Performance Analysis Module

- [x] 5.1 Implement core metrics calculation (cumulative return, annualized return, volatility, max drawdown).
- [x] 5.2 Implement drawdown path and drawdown duration analysis.
- [x] 5.3 Implement risk-adjusted metrics (Sharpe, Sortino, Calmar) with explicit assumption metadata.
- [x] 5.4 Implement batch ranking by selected objective and cross-window comparison output.

## 6. Verification And Acceptance

- [x] 6.1 Add acceptance tests for each new capability scenario in OpenSpec specs.
- [x] 6.2 Add end-to-end fixture covering mixed-currency assets and constrained portfolio generation.
- [x] 6.3 Document default assumptions (calendar alignment, missing data policy, metric parameters).
