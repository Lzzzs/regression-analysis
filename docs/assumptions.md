# Default Assumptions

- Calendar alignment: asset-calendar-driven valuation. Missing data on expected trading days fails fast.
- Missing data policy:
- Expected trading day price/FX missing => fail run.
- Market closed day => stale valuation allowed from last available close/rate, and no trade for closed assets.
- Metric parameters:
- Trading days per year: 252.
- Risk-free rate: 0.0 by default.
- Snapshot policy:
- Daily incremental ingestion.
- Weekly frozen snapshot publish on Friday.
- Backtest input must provide immutable `snapshot_id`.
