## ADDED Requirements

### Requirement: Queue consumption and execution
The system SHALL run a worker process that consumes queued jobs and executes backtests using the existing engine.

#### Scenario: Process queued job
- **WHEN** the worker finds a queued job record
- **THEN** the worker marks it running, executes backtest, and persists result artifact

### Requirement: Failure handling
The system SHALL persist failure reason and mark job failed when execution raises an error.

#### Scenario: Record execution error
- **WHEN** backtest execution fails for a job
- **THEN** the worker stores error message and sets job status to failed

### Requirement: Reproducibility fields propagation
The system SHALL propagate `snapshot_id`, input hash, and run metadata into job result records.

#### Scenario: Inspect completed job provenance
- **WHEN** a client reads a completed job result
- **THEN** result includes `snapshot_id`, run id, and metadata required for reproducibility
