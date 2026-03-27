## Why

当前任务队列使用文件扫描，吞吐和并发能力有限，也缺少标准化重试与死信处理。需要引入可切换的 Redis 队列后端，在不破坏现有功能的前提下提升任务调度可靠性与可扩展性。

## What Changes

- 新增队列后端抽象，支持 `file` 与 `redis` 两种实现。
- 新增 Redis 队列后端，支持任务入队、抢占、状态更新和结果读取。
- 新增失败重试机制与最大重试次数控制。
- 新增死信状态与死信队列记录，便于排障与后续补偿。
- 新增配置开关与文档，支持通过环境变量切换后端与参数。

## Capabilities

### New Capabilities

- `redis-job-queue-backend`: 基于 Redis 的任务队列存取与状态管理能力。
- `job-retry-dead-letter`: 任务失败重试与死信归档能力。

### Modified Capabilities

- `api-job-orchestration`: 任务编排能力扩展为可切换后端并暴露重试字段与死信状态。
- `worker-backtest-execution`: Worker 执行流程扩展为重试驱动与死信落地。

## Impact

- 影响 `apps/api` 和 `apps/worker` 的存储与执行路径。
- 新增 Redis 可选依赖与配置项（`JOB_QUEUE_BACKEND`, `REDIS_URL`, `JOB_MAX_RETRIES`）。
- 影响 API 返回状态集合（新增 `dead-letter`）。
