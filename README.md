# Portfolio Lab

一个离线优先（offline-first）的组合回测实验室，支持：
- 自定义权重组合（A 股 / 美股 / 加密等资产混合）
- 自动生成快照并提交回测任务（`/jobs/auto`）
- 任务队列、重试、死信（Redis/File 双后端）
- Web 端中文化展示（含未知字段兜底）
- 结果可视化（核心指标卡片 + 净值/回撤曲线）

## 架构

- `apps/web`：Next.js 前端（提交组合、查看任务、查看结果）
- `apps/api`：FastAPI 接口（建任务、查状态、查结果、死信重试）
- `apps/worker`：回测后台 worker（消费队列并执行）
- `src/portfolio_lab`：回测引擎与数据域模型
- `data/providers/*.csv`：默认离线数据源样例

## 快速开始（本地）

### 1) 前置依赖

- Python 3.10+
- Node.js 18+
- Redis（推荐，用于可靠队列）

### 2) 一键启动

```bash
cp .env.example .env
cp apps/web/.env.local.example apps/web/.env.local
bash scripts/dev_up.sh
```

启动后访问：
- Web: `http://127.0.0.1:3000`
- API: `http://127.0.0.1:8000`

停止：

```bash
bash scripts/dev_down.sh
```

## 手动启动（可选）

```bash
# API
JOB_QUEUE_BACKEND=redis REDIS_URL=redis://127.0.0.1:6379/0 JOB_MAX_RETRIES=1 \
PYTHONPATH=.:src .venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000

# Worker
JOB_QUEUE_BACKEND=redis REDIS_URL=redis://127.0.0.1:6379/0 JOB_MAX_RETRIES=1 \
PYTHONPATH=.:src .venv/bin/python -m apps.worker.runner

# Web
cd apps/web
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000
```

## 常用 API

- `GET /health`
- `POST /jobs`
- `POST /jobs/auto`
- `GET /jobs`
- `GET /jobs/dead-letter`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/result`
- `POST /jobs/{job_id}/requeue`
- `POST /snapshots/from-providers`

## 测试与构建

```bash
PYTHONPATH=.:src .venv/bin/python -m unittest
cd apps/web && npm run build
```

## 部署建议（GitHub + Vercel）

- Web 部署到 Vercel（连接 `apps/web`）
- API/Worker/Redis 部署到常驻计算平台（Railway / Render / Fly.io）
- 不建议把 Python Worker 放在 Vercel Serverless 上长期执行
- GitHub Actions 负责 CI（Python 单测 + Web build）

## 数据准确性说明

- 回测任务基于不可变 `snapshot_id` 执行，结果可复算
- 默认样例数据在 `data/providers/*.csv`
- 生产环境建议引入 provider 拉取 + 快照审计（来源、时间、checksum）
