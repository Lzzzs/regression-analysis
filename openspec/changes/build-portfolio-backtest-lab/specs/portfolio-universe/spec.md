## ADDED Requirements

### Requirement: Asset universe registration
The system SHALL allow users to register and maintain a universe of assets for experiments, including unique identifier, asset type, market, trading calendar, quote currency, and optional tags.

#### Scenario: Add an asset into universe
- **WHEN** a user submits an asset definition with all required metadata
- **THEN** the system stores the asset as an active member of the universe

#### Scenario: Reject duplicate asset identifier
- **WHEN** a user submits an asset definition whose identifier already exists
- **THEN** the system MUST reject the request with a duplicate identifier error

### Requirement: Price series normalization
The system SHALL ingest asset price data into a normalized daily series format with explicit date, close value, and data-source metadata.

#### Scenario: Import valid daily prices
- **WHEN** a user imports a daily price series with valid dates and numeric close values
- **THEN** the system stores a normalized time series linked to that asset

#### Scenario: Reject malformed price row
- **WHEN** a price row is missing date or close value
- **THEN** the system MUST reject that import batch and report row-level validation errors

### Requirement: Versioned snapshot publishing
The system SHALL publish versioned offline market-data snapshots that include asset prices and required FX series for a declared coverage range.

#### Scenario: Publish a complete snapshot
- **WHEN** data ingestion for selected assets and FX pairs is complete for the target range
- **THEN** the system creates a new snapshot with a unique `snapshot_id` and immutable data references

#### Scenario: Reject incomplete snapshot publish
- **WHEN** required asset price or FX series is missing for the declared snapshot coverage policy
- **THEN** the system MUST reject snapshot publish and report missing datasets

### Requirement: Snapshot release cadence
The system SHALL support daily incremental ingestion and weekly frozen snapshot release as the default research cadence.

#### Scenario: Build weekly frozen snapshot from daily increments
- **WHEN** daily ingestion has accumulated updates for the current week
- **THEN** the system publishes one immutable weekly snapshot with a unique `snapshot_id`

### Requirement: Snapshot quality gates
The system SHALL apply quality gates before snapshot publish, including expected-trading-day completeness and source traceability.

#### Scenario: Reject snapshot with trading-day gap
- **WHEN** an asset has missing close prices on expected trading days within snapshot coverage
- **THEN** the system MUST reject publish and return a gap report with asset and date details

### Requirement: Calendar and currency metadata exposure
The system SHALL expose each asset's trading calendar and quote currency so downstream modules can align valuation dates and FX conversion.

#### Scenario: Query asset metadata for backtest planning
- **WHEN** a backtest module requests universe metadata for selected assets
- **THEN** the system returns trading calendar and quote currency for every selected asset
