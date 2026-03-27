## ADDED Requirements

### Requirement: Market-based provider routing
The system MUST route each requested asset to a configured market-specific price provider.

#### Scenario: Route A-share, US, and crypto assets
- **WHEN** selected assets contain mixed markets and provider mappings are configured
- **THEN** the adapter fetches rows from the corresponding provider per market and returns unified ingestion rows

### Requirement: Provider mapping validation
The system MUST reject ingestion when market/provider mapping is incomplete.

#### Scenario: Missing provider for mapped market
- **WHEN** an asset resolves to a market that has no registered provider
- **THEN** ingestion fails with a validation error identifying the missing market mapping
