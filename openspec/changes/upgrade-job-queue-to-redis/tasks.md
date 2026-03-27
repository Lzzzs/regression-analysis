## 1. Queue Abstraction

- [x] 1.1 Introduce queue backend interface and refactor `JobStore` to delegate operations.
- [x] 1.2 Keep file backend compatible with current behavior while adding retry/dead-letter fields.

## 2. Redis Backend

- [x] 2.1 Implement Redis backend for create/get/update/list/claim/result operations.
- [x] 2.2 Add backend selection by env vars (`JOB_QUEUE_BACKEND`, `REDIS_URL`).

## 3. Retry And Dead-Letter

- [x] 3.1 Add `retry_count` and `max_retries` handling in failure path.
- [x] 3.2 Requeue on retryable failure and move to dead-letter on exhaustion.
- [x] 3.3 Ensure API status response includes retry and dead-letter state fields.

## 4. Tests And Docs

- [x] 4.1 Add tests for retry and dead-letter transitions.
- [x] 4.2 Add tests for Redis backend using an in-memory fake Redis client.
- [x] 4.3 Update deployment docs with queue backend and retry environment variables.
