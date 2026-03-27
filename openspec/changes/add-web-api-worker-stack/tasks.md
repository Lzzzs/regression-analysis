## 1. Monorepo App Scaffolding

- [x] 1.1 Create `apps/web`, `apps/api`, and `apps/worker` directory structure with runnable entry files.
- [x] 1.2 Add shared contract module for job request/response payload schemas.

## 2. API Job Orchestration

- [x] 2.1 Implement job creation endpoint with payload validation and `job_id` generation.
- [x] 2.2 Implement job status endpoint returning lifecycle timestamps and status.
- [x] 2.3 Implement job result endpoint returning completed run metadata, metrics, and equity curve.
- [x] 2.4 Add file-based queue/repository layer for queued/running/completed/failed state transitions.

## 3. Worker Execution

- [x] 3.1 Implement worker loop to consume queued jobs and mark running/completed states.
- [x] 3.2 Integrate worker execution with existing `portfolio_lab` backtest engine.
- [x] 3.3 Persist failure reason and failed status for execution exceptions.

## 4. Web Experiment Console

- [x] 4.1 Implement experiment submission page with required fields including `snapshot_id`.
- [x] 4.2 Implement job detail page with status polling and lifecycle display.
- [x] 4.3 Implement result view for core metrics and equity curve payload rendering.

## 5. Delivery And Verification

- [x] 5.1 Add GitHub Actions workflow for tests and offline backtest guard checks.
- [x] 5.2 Add Vercel deployment config for web preview and production deployment.
- [x] 5.3 Add integration tests covering API submit/status/result and worker processing flow.
- [x] 5.4 Add documentation for local run flow and GitHub/Vercel deployment variables.
