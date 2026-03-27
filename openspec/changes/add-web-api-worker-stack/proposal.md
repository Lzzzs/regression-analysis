## Why

当前项目已经有可用的回测内核，但缺少可部署的交互入口和任务执行编排，无法通过 GitHub 持续交付到线上环境。需要补齐 Web/API/Worker 三层与部署链路，让用户可以在网页上提交实验并查看结果。

## What Changes

- 新增 Web 前端应用，支持实验配置、任务提交、任务状态与结果展示。
- 新增 API 服务，负责实验请求校验、任务入队、任务状态查询和结果查询。
- 新增 Worker 执行器，负责消费任务并调用现有回测内核执行。
- 新增任务存储与快照引用契约，确保以 `snapshot_id` 为中心的可复现执行。
- 新增 GitHub + Vercel 部署配置与 CI 检查，支持预览部署与主干自动发布。

## Capabilities

### New Capabilities

- `web-experiment-console`: 提供浏览器端实验配置、提交、运行状态与结果可视化。
- `api-job-orchestration`: 提供任务提交、状态查询、结果读取等后端接口与校验逻辑。
- `worker-backtest-execution`: 提供异步任务消费与回测执行流程，产出可追溯结果。
- `github-vercel-delivery`: 提供 GitHub 驱动 CI 与 Vercel 部署流水线。

### Modified Capabilities

- None.

## Impact

- 新增 `apps/web`、`apps/api`、`apps/worker` 工程结构与共享契约模块。
- 新增任务元数据与运行结果索引文件，连接回测核心模块与前端展示。
- 引入 Next.js/FastAPI 等运行时依赖，以及 GitHub Actions / Vercel 配置文件。
