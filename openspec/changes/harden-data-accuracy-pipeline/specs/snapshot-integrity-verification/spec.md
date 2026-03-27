## ADDED Requirements

### Requirement: Snapshot checksum generation
The system MUST generate and persist a deterministic checksum for each published snapshot.

#### Scenario: Publish snapshot with integrity metadata
- **WHEN** a weekly snapshot is published
- **THEN** snapshot payload includes `integrity.algorithm` and `integrity.checksum_sha256`

### Requirement: Snapshot checksum verification
The system MUST verify snapshot checksum before use.

#### Scenario: Tampered snapshot rejected
- **WHEN** snapshot content is modified after publication
- **THEN** loading or backtesting with that snapshot fails with a snapshot integrity error
