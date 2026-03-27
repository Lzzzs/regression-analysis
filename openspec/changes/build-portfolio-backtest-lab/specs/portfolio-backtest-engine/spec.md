## ADDED Requirements

### Requirement: Time-range backtest execution
The system SHALL execute portfolio backtests over a user-defined date range with configurable rebalance frequency using a declared offline `snapshot_id`.

#### Scenario: Run monthly rebalance backtest
- **WHEN** a user starts a backtest with a date range, monthly rebalance frequency, and valid `snapshot_id`
- **THEN** the system produces a portfolio equity curve covering the requested range

#### Scenario: Run buy-and-hold backtest
- **WHEN** a user starts a backtest with rebalance frequency set to none and valid `snapshot_id`
- **THEN** the system performs initial allocation only and outputs an equity curve without rebalance trades

#### Scenario: Reject run without snapshot reference
- **WHEN** a user starts a backtest request without `snapshot_id`
- **THEN** the system MUST reject the request with a missing snapshot reference error

### Requirement: Cost-aware trade accounting
The system SHALL apply configured transaction cost and slippage models to each rebalance trade before computing portfolio value.

#### Scenario: Apply transaction cost at rebalance
- **WHEN** a rebalance requires trade execution and a non-zero fee model is configured
- **THEN** the system deducts costs from cash and reflects the deduction in equity values

### Requirement: Multi-currency valuation
The system SHALL value all holdings in a single base currency using declared FX series and valuation timestamp rules.

#### Scenario: Convert USD asset into CNY base valuation
- **WHEN** a backtest base currency is CNY and an asset quote currency is USD
- **THEN** the system converts the asset value using configured USD/CNY FX data for each valuation point

#### Scenario: Missing FX value handling
- **WHEN** FX data is unavailable for a required valuation point
- **THEN** the system MUST apply the configured missing-FX policy and record that policy usage in run metadata

### Requirement: Accuracy-first missing data policy
The system SHALL fail backtest execution by default when price or FX data is missing on expected trading days and SHALL NOT forward-fill or interpolate such gaps.

#### Scenario: Fail on missing price for expected trading day
- **WHEN** an asset has no price on a date that is an expected trading day under its calendar
- **THEN** the run MUST fail with a missing-price error report containing asset and date

#### Scenario: Allow stale valuation on market-closed day
- **WHEN** an asset market is closed on a valuation date and no new close exists
- **THEN** the engine carries forward last available close for valuation, marks stale valuation, and MUST NOT execute rebalance trade for that asset on that date

#### Scenario: Fail on missing FX for expected trading day
- **WHEN** base-currency conversion is required and FX value is missing on an expected trading day
- **THEN** the run MUST fail with a missing-FX error report containing pair and date

### Requirement: Reproducible run metadata
The system SHALL persist run metadata including input specs, data version identifiers, and execution timestamp for reproducibility.

#### Scenario: Inspect completed run metadata
- **WHEN** a user requests run details for a completed backtest
- **THEN** the system returns all input specs and data version references used for that run

### Requirement: No external data fetch during run
The system SHALL execute backtests without calling external market-data APIs during run time.

#### Scenario: Execute run from local snapshot only
- **WHEN** a backtest run starts with a valid `snapshot_id`
- **THEN** the engine reads all required prices and FX values from snapshot storage without outbound market-data API calls
