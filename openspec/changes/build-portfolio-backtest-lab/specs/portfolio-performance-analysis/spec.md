## ADDED Requirements

### Requirement: Core return and risk metrics
The system SHALL compute core performance metrics for each completed backtest run, including cumulative return, annualized return, annualized volatility, and maximum drawdown.

#### Scenario: Generate core metrics for one run
- **WHEN** a backtest run completes with a valid equity curve
- **THEN** the system returns all core return and risk metrics for that run

### Requirement: Drawdown path analysis
The system SHALL compute drawdown time series and longest drawdown duration for each run.

#### Scenario: Report drawdown duration
- **WHEN** a run contains a drawdown period that has not fully recovered by the end date
- **THEN** the system reports the active drawdown duration through the end date

### Requirement: Risk-adjusted performance metrics
The system SHALL compute risk-adjusted metrics including Sharpe ratio, Sortino ratio, and Calmar ratio using documented assumptions.

#### Scenario: Compute risk-adjusted metrics with default assumptions
- **WHEN** a user requests analysis without custom metric parameters
- **THEN** the system computes Sharpe, Sortino, and Calmar using default assumptions and documents those assumptions in output metadata

### Requirement: Batch ranking and comparison
The system SHALL support ranking multiple portfolio runs by user-selected objective metrics and support cross-window comparison views.

#### Scenario: Rank batch by Calmar ratio
- **WHEN** a batch experiment contains multiple run results and ranking objective is Calmar
- **THEN** the system returns a sorted ranking list by Calmar ratio

#### Scenario: Compare same portfolio across multiple windows
- **WHEN** a user requests cross-window comparison for one portfolio identifier
- **THEN** the system returns that portfolio's metric summary for each selected window in one comparison result set
