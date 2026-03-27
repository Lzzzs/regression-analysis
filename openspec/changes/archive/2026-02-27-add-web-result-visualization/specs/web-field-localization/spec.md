## ADDED Requirements

### Requirement: Chinese field rendering for job-related payloads
The system SHALL render job-related fields in Chinese on web pages that display job status and backtest output.

#### Scenario: Localize known fields and enums
- **WHEN** the page renders status, payload summary, metrics, and timeline events
- **THEN** known field names and enum-like values are shown in Chinese equivalents

### Requirement: Future-field localization fallback
The system SHALL provide a readable Chinese fallback for unknown/new fields without requiring immediate frontend release.

#### Scenario: Render unknown field key from API
- **WHEN** a previously unseen key appears in job payload or result JSON
- **THEN** the web app applies token-based fallback localization so the displayed key is human-readable in Chinese
