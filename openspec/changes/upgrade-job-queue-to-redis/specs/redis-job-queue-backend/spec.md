## ADDED Requirements

### Requirement: Configurable queue backend
The system SHALL support selecting queue backend via configuration, with `file` and `redis` as valid values.

#### Scenario: Start with file backend
- **WHEN** `JOB_QUEUE_BACKEND` is unset or set to `file`
- **THEN** the system uses file-backed queue behavior

#### Scenario: Start with redis backend
- **WHEN** `JOB_QUEUE_BACKEND` is set to `redis`
- **THEN** the system uses Redis-backed queue behavior for job enqueue and claim

### Requirement: Redis job persistence and queue operations
The system SHALL persist job records in Redis and enqueue/dequeue job ids through Redis queue keys.

#### Scenario: Create and claim queued job in Redis
- **WHEN** API creates a new job under Redis backend and worker claims next queued job
- **THEN** worker receives the created job and status transitions to running
