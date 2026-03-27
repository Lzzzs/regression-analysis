## ADDED Requirements

### Requirement: Job creation API
The system SHALL provide an API endpoint to validate experiment payloads and enqueue a backtest job.

#### Scenario: Create job successfully
- **WHEN** a client sends a valid job creation request
- **THEN** the API validates payload, writes a queued job record, and returns a unique `job_id`

#### Scenario: Reject invalid payload
- **WHEN** a client sends invalid weights or missing `snapshot_id`
- **THEN** the API MUST reject the request with validation error details

### Requirement: Job status API
The system SHALL provide an API endpoint to fetch current job status and timestamps.

#### Scenario: Query existing job status
- **WHEN** a client requests status for an existing `job_id`
- **THEN** the API returns one of queued/running/completed/failed with lifecycle timestamps

### Requirement: Job result API
The system SHALL provide an API endpoint to fetch completed run outputs by `job_id`.

#### Scenario: Fetch completed job result
- **WHEN** a client requests result for a completed job
- **THEN** the API returns run metadata, metrics, and equity curve payload
