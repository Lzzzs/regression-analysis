## ADDED Requirements

### Requirement: GitHub CI verification
The system SHALL run automated checks on pull requests, including tests for offline backtest constraints.

#### Scenario: Run CI on pull request
- **WHEN** a pull request is opened or updated
- **THEN** CI executes test suite and reports pass/fail status before merge

### Requirement: Vercel web deployment
The system SHALL support Vercel deployment for the web app with preview on pull requests and production on main branch.

#### Scenario: Preview deployment on pull request
- **WHEN** a pull request updates web code
- **THEN** Vercel creates a preview deployment and exposes a preview URL

#### Scenario: Production deployment on main
- **WHEN** changes are merged into main branch
- **THEN** Vercel deploys the web app to production environment
