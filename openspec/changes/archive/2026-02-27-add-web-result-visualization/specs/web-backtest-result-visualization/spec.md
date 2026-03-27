## ADDED Requirements

### Requirement: Core metric cards for completed jobs
The system SHALL display key backtest metrics as prominent cards on the job detail page after a job is completed.

#### Scenario: Render metric cards from completed result
- **WHEN** a job detail request returns status `completed` and contains numeric metrics
- **THEN** the web page shows metric cards for key indicators (including annualized return, annualized volatility, max drawdown, and risk-adjusted ratios)

### Requirement: Equity and drawdown trend visualization
The system SHALL visualize equity and drawdown trends for completed jobs.

#### Scenario: Render equity and drawdown charts
- **WHEN** a completed job result contains `equity_curve`
- **THEN** the web page renders an equity line chart and a drawdown line chart with start/end labels and min/max summary

### Requirement: Detail view remains auditable
The system SHALL keep detailed result data visible alongside charts.

#### Scenario: Show chart and structured details together
- **WHEN** charts are rendered for a completed job
- **THEN** the page still provides structured metric details and equity samples for cross-checking
