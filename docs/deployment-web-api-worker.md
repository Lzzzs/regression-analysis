# Web/API/Worker Deployment Notes

## Local Run

1. Copy env examples:
   - `cp .env.example .env`
   - `cp apps/web/.env.local.example apps/web/.env.local`
2. One-click startup:
   - `bash scripts/dev_up.sh`
3. One-click stop:
   - `bash scripts/dev_down.sh`

### Manual commands (optional)

- API:
  - `JOB_QUEUE_BACKEND=redis REDIS_URL=redis://127.0.0.1:6379/0 JOB_MAX_RETRIES=1 PYTHONPATH=.:src .venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000`
- Worker:
  - `JOB_QUEUE_BACKEND=redis REDIS_URL=redis://127.0.0.1:6379/0 JOB_MAX_RETRIES=1 PYTHONPATH=.:src .venv/bin/python -m apps.worker.runner`
- Web:
  - `cd apps/web && NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000`

## Environment Variables

- `NEXT_PUBLIC_API_BASE_URL`: public API base URL for web frontend.
- `JOB_QUEUE_BACKEND`: `file` (default) or `redis`.
- `REDIS_URL`: Redis connection URL used when `JOB_QUEUE_BACKEND=redis`.
- `JOB_MAX_RETRIES`: max retry count before moving job to `dead-letter` (default `1`).

## GitHub + Vercel

- GitHub Actions workflow in `.github/workflows/ci.yml` runs tests on PR and main.
- Connect `apps/web` project to Vercel.
- Vercel preview deployments are created automatically for PRs.
- Production deploy happens when PR is merged to `main`.

## API Endpoints

- `GET /health`: API health.
- `POST /jobs`: create job.
- `POST /jobs/auto`: auto create snapshot then queue job.
- `GET /jobs`: list jobs (`status`, `q`, `limit`, `offset` query supported).
- `GET /jobs/dead-letter`: list dead-letter jobs (`q`, `limit`, `offset` query supported).
- `GET /jobs/{job_id}`: get status.
- `POST /jobs/{job_id}/requeue`: requeue dead-letter/failed job.
- `GET /jobs/{job_id}/result`: get completed result.
