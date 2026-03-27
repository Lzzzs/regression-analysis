## ADDED Requirements

### Requirement: Fixed-weight portfolio definition
The system SHALL allow users to define a portfolio with explicit asset weights where total target weight MUST equal 100% within configured tolerance.

#### Scenario: Create valid fixed-weight portfolio
- **WHEN** a user defines weights that sum to 100% within tolerance
- **THEN** the system stores the portfolio as a valid executable allocation

#### Scenario: Reject invalid total weight
- **WHEN** a user defines weights whose sum violates the total weight tolerance
- **THEN** the system MUST reject the portfolio and return a weight sum validation error

### Requirement: Constraint-based portfolio generation
The system SHALL support parameterized portfolio generation from weight ranges and constraints, including per-asset cap, group cap, and minimum cash allocation.

#### Scenario: Generate candidate portfolios from ranges
- **WHEN** a user submits parameter ranges and valid constraints
- **THEN** the system returns all candidate portfolios that satisfy every constraint

#### Scenario: Exclude portfolio violating BTC cap
- **WHEN** a generated candidate has BTC weight above configured BTC cap
- **THEN** the system MUST exclude that candidate from executable outputs

### Requirement: Deterministic portfolio identity
The system SHALL assign deterministic portfolio identifiers based on normalized composition so the same composition produces the same identifier across runs.

#### Scenario: Reuse same composition in separate experiments
- **WHEN** two experiments include portfolios with identical normalized weights
- **THEN** both experiments receive the same portfolio identifier for that composition
