## 1. Data Adapter Layer

- [x] 1.1 Add `MarketDataAdapter` protocol and local fixture adapter implementation.
- [x] 1.2 Add `UniverseStore.ingest_from_adapter(...)` to fetch and ingest by date range.

## 2. Ingestion Validation Hardening

- [x] 2.1 Add batch duplicate-key conflict checks for prices and FX ingestion.
- [x] 2.2 Add non-crypto trading-day alignment validation before accepting rows.

## 3. Snapshot Integrity

- [x] 3.1 Add deterministic snapshot checksum generation during publish.
- [x] 3.2 Add checksum verification in snapshot loading and backtest entry path.

## 4. Tests

- [x] 4.1 Add tests for adapter ingestion and duplicate-key rejection.
- [x] 4.2 Add tests for weekend non-crypto rejection and tampered snapshot rejection.
