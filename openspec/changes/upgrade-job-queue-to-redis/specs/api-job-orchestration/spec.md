## MODIFIED Requirements

### Requirement: Job status API
The system SHALL provide an API endpoint to fetch current job status and timestamps.

#### Scenario: Query existing job status
- **WHEN** a client requests status for an existing `job_id`
- **THEN** the API returns one of queued/running/completed/failed/dead-letter with lifecycle timestamps and retry fields
