## ADDED Requirements

### Requirement: Adapter-based market data ingestion
The system MUST support ingesting price and FX rows via a pluggable market-data adapter interface.

#### Scenario: Ingest from adapter
- **WHEN** an adapter is provided with a date range and selected assets/fx pairs
- **THEN** the system ingests returned prices and FX into the universe store using existing validation rules

### Requirement: Offline adapter support
The system MUST provide an offline adapter implementation backed by local JSON fixtures.

#### Scenario: Load offline fixture
- **WHEN** the offline adapter reads fixture files for prices and FX
- **THEN** it returns normalized rows with required fields (`asset_id/pair`, `day`, `close/rate`, `source`)
