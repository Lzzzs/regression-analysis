## 1. Provider Interfaces

- [x] 1.1 Add `PriceDataProvider` and `FXDataProvider` protocols.
- [x] 1.2 Add CSV-backed provider implementations for price and FX rows.

## 2. Routing Adapter

- [x] 2.1 Add `RoutedMarketDataAdapter` with `asset_market_map` and `asset_symbol_map` support.
- [x] 2.2 Add normalization and validation for provider output rows.

## 3. Integration

- [x] 3.1 Export new provider and adapter types via package `__init__`.

## 4. Tests

- [x] 4.1 Add test for multi-market routed ingestion success path.
- [x] 4.2 Add test for missing provider mapping failure path.
