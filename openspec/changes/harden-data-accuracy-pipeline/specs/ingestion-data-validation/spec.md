## ADDED Requirements

### Requirement: Duplicate key conflict detection
The system MUST reject ingestion batches containing conflicting duplicate records.

#### Scenario: Conflicting duplicate price row
- **WHEN** a batch contains two rows with same `(asset_id, day)` but different `close` values
- **THEN** ingestion fails with a validation error including the conflicted key

### Requirement: Trading-day alignment validation
The system MUST validate that non-crypto assets are only ingested on expected trading days.

#### Scenario: Weekend non-crypto row
- **WHEN** a non-crypto asset row is ingested on a weekend day
- **THEN** ingestion fails with a validation error indicating calendar mismatch
