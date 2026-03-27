## MODIFIED Requirements

### Requirement: Failure handling
The system SHALL persist failure reason and mark job failed when execution raises an error.

#### Scenario: Retry then dead-letter
- **WHEN** worker repeatedly fails a job
- **THEN** the system retries until limit and finally marks the job as dead-letter with final error details
