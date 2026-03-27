## ADDED Requirements

### Requirement: Experiment submission UI
The system SHALL provide a web form for users to submit experiment payloads, including weights, backtest window, rebalance frequency, and `snapshot_id`.

#### Scenario: Submit valid experiment
- **WHEN** a user submits a valid experiment form
- **THEN** the web app sends a create-job request and displays the returned `job_id`

### Requirement: Job status polling
The system SHALL allow users to track job progress from the web UI.

#### Scenario: View pending and running status
- **WHEN** a user opens a submitted job detail view
- **THEN** the web app polls job status endpoint and renders pending/running/completed/failed states

### Requirement: Result visualization
The system SHALL display core metrics and equity curve summary for completed jobs.

#### Scenario: Show completed backtest output
- **WHEN** a job transitions to completed
- **THEN** the web app renders core metrics and an equity curve data view for that run
