## Context

现有任务编排使用文件目录轮询，Worker 通过扫描 `queued` 状态领取任务。该模式简单但并发一致性与吞吐受限，也无法优雅支持重试和死信策略。当前系统已形成 API->Worker->Result 闭环，因此本次重点是替换底层队列实现而非重写业务流程。

## Goals / Non-Goals

**Goals:**
- 定义统一队列后端接口，支持文件和 Redis 两类实现。
- 增加失败重试与死信机制，避免瞬时失败直接终止任务生命周期。
- 通过配置切换后端，保持现有 API/Worker 调用层尽量少改动。

**Non-Goals:**
- 不引入分布式事务。
- 不在本次实现优先级队列与延时队列。
- 不要求无 Redis 时必须安装额外依赖。

## Decisions

### 1) 引入 `QueueBackend` 抽象
- 决策：将 `JobStore` 从“文件实现”重构为“后端代理 + 统一接口”。
- 原因：降低 API/Worker 对存储细节耦合，后续替换成本低。
- 备选：直接在 `JobStore` 中写 Redis 分支逻辑，会导致类复杂度快速膨胀。

### 2) Redis 后端采用“记录键 + 队列键”模式
- 决策：`job:<id>` 存记录，`jobs:queued` 存排队 job_id，`jobs:dead` 存死信 job_id。
- 原因：读写路径清晰，支持状态查询与队列消费分离。
- 备选：单一大 JSON key，不利于并发领取和列表操作。

### 3) 重试策略内聚在 `mark_failed`
- 决策：失败时如果 `retry_count < max_retries`，回写 `queued` 并递增计数；否则转 `dead-letter`。
- 原因：Worker 逻辑保持简单，不需要感知重试阈值细节。
- 备选：Worker 外层循环判断，职责分散。

### 4) 保持文件后端作为默认回退
- 决策：默认 `JOB_QUEUE_BACKEND=file`，Redis 为显式开启。
- 原因：本地开发无 Redis 也能运行，降低使用门槛。
- 备选：默认 Redis，部署前置依赖过重。

## Risks / Trade-offs

- [Redis 不可用导致服务不可用] -> 默认文件后端回退，Redis 模式启动时显式报错。
- [重试风暴] -> 增加 `JOB_MAX_RETRIES` 上限并把错误写入记录。
- [状态不一致] -> 统一由后端实现管理状态迁移并提供集成测试覆盖。

## Migration Plan

1. 抽取后端接口与文件后端适配。
2. 增加 Redis 后端实现与配置解析。
3. 接入 Worker 失败重试与死信逻辑。
4. 增加集成测试覆盖 file/redis 路径。
5. 更新部署文档与环境变量说明。

## Open Questions

- 生产默认 `JOB_MAX_RETRIES` 取 1 还是 3？
