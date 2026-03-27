## ADDED Requirements

### Requirement: Retry on execution failure
The system SHALL retry failed jobs until `retry_count` reaches configured `max_retries`.

#### Scenario: Requeue transient failure
- **WHEN** worker execution fails and `retry_count` is below `max_retries`
- **THEN** the job status MUST return to queued with incremented `retry_count`

### Requirement: Dead-letter on retry exhaustion
The system SHALL move jobs to dead-letter state after retries are exhausted.

#### Scenario: Mark dead-letter
- **WHEN** worker execution fails and `retry_count` has reached `max_retries`
- **THEN** the job status MUST become `dead-letter` and include final error message
