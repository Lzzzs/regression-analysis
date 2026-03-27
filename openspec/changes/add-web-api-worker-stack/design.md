## Context

现有项目已具备离线快照回测核心能力与测试，但仍是库级实现，缺少可交互入口与异步执行编排。要支持 GitHub 驱动部署，需补齐三层架构：Web 前端（Vercel）、API 编排层（任务提交与查询）、Worker 执行层（消费任务并调用回测核心）。

## Goals / Non-Goals

**Goals:**
- 提供可部署的 Web 控制台，支持实验配置、提交、查看状态和结果。
- 提供 API 层统一处理请求校验、任务入队、状态/结果查询。
- 提供 Worker 进程异步执行回测任务，输出可追溯运行结果。
- 提供最小可用的 GitHub CI 与 Vercel 部署配置，支持 PR 预览和主分支部署。

**Non-Goals:**
- 不在本变更中实现复杂鉴权与多租户隔离。
- 不引入外部消息队列服务（先使用本地文件队列实现可替换接口）。
- 不改动回测核心策略与指标定义。

## Decisions

### 1) Monorepo 结构：`apps/web` + `apps/api` + `apps/worker`
- 决策：采用应用分层目录，保留 `src/portfolio_lab` 为回测核心包。
- 原因：部署与职责边界清晰，后续可独立扩展服务。
- 备选：单体 API + 模板页面，初期简单但不利于 Vercel 前端演进。

### 2) API 采用 FastAPI，同步入队，异步执行
- 决策：API 负责参数校验并落地任务文件，立即返回 `job_id`；Worker 轮询队列并执行。
- 原因：易于实现、无额外基础设施依赖，符合当前准确性优先和可审计要求。
- 备选：Redis/Celery，扩展性更高但当前工程复杂度过大。

### 3) Worker 与核心引擎进程内复用
- 决策：Worker 直接调用 `portfolio_lab` 的 `UniverseStore` 和 `BacktestEngine`。
- 原因：避免重复实现，确保与已验证内核一致。
- 备选：通过 HTTP 调用内核服务，解耦但增加链路复杂度。

### 4) Web 使用 Next.js（App Router）对接 API
- 决策：Web 层采用 Next.js + TypeScript，页面包含实验表单、任务状态轮询、结果图表占位。
- 原因：与 Vercel 部署流程天然匹配，便于后续接入更复杂前端交互。
- 备选：静态 HTML，开发快但扩展性差。

### 5) GitHub CI 强制“离线回测”约束
- 决策：CI 中运行单元测试，并新增无网络执行校验测试。
- 原因：防止后续改动破坏“回测执行时不访问外部接口”的核心约束。
- 备选：仅 lint，无法保护关键运行约束。

## Risks / Trade-offs

- [文件队列并发吞吐有限] -> 定义抽象接口，后续可替换 Redis/SQS。
- [API 与 Worker 进程崩溃导致任务残留] -> 通过任务状态文件与重试次数字段支持恢复。
- [Web 与 API 契约漂移] -> 增加共享请求/响应 schema 与契约测试。
- [部署环境差异导致路径问题] -> 将数据路径与 API 地址配置为环境变量。

## Migration Plan

1. 建立 `apps/web`、`apps/api`、`apps/worker` 结构与基础运行入口。
2. 打通 API 提交任务 -> Worker 执行 -> 结果查询闭环。
3. 对接 Web 表单与任务/结果接口，实现最小可用界面。
4. 增加 GitHub Actions 与 Vercel 配置，验证 PR 预览与主干部署。
5. 验证后逐步替换文件队列为可扩展队列（后续变更）。

## Open Questions

- 生产环境 Worker 托管优先选 Render 还是 Cloud Run？
- 任务重试策略默认次数是 1 次还是 3 次？
