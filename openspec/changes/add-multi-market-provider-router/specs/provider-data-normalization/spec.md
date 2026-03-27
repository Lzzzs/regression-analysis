## ADDED Requirements

### Requirement: Provider output normalization
The system MUST normalize provider rows into the canonical ingestion schema.

#### Scenario: Normalize price row
- **WHEN** a price provider returns `day/close/source` rows for a symbol
- **THEN** adapter outputs rows containing `asset_id`, normalized `day`, numeric positive `close`, and non-empty `source`

### Requirement: Adapter-level data validity checks
The system MUST validate basic provider output constraints before ingestion.

#### Scenario: Reject non-positive rate
- **WHEN** FX provider returns a row with non-positive `rate`
- **THEN** adapter fails with validation error and does not return invalid rows
