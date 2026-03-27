#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

RUNTIME_DIR="${ROOT_DIR}/.runtime"
mkdir -p "${RUNTIME_DIR}"

JOB_QUEUE_BACKEND="${JOB_QUEUE_BACKEND:-redis}"
REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
JOB_MAX_RETRIES="${JOB_MAX_RETRIES:-1}"
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
WEB_PORT="${WEB_PORT:-3000}"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

if ! .venv/bin/python -c "import fastapi, uvicorn, redis" >/dev/null 2>&1; then
  .venv/bin/pip install fastapi uvicorn redis
fi

if [ ! -d "apps/web/node_modules" ]; then
  (cd apps/web && npm install)
fi

if [ -f "${RUNTIME_DIR}/api.pid" ]; then
  kill "$(cat "${RUNTIME_DIR}/api.pid")" >/dev/null 2>&1 || true
fi
if [ -f "${RUNTIME_DIR}/worker.pid" ]; then
  kill "$(cat "${RUNTIME_DIR}/worker.pid")" >/dev/null 2>&1 || true
fi
if [ -f "${RUNTIME_DIR}/web.pid" ]; then
  kill "$(cat "${RUNTIME_DIR}/web.pid")" >/dev/null 2>&1 || true
fi

nohup /bin/zsh -lc \
  "JOB_QUEUE_BACKEND=${JOB_QUEUE_BACKEND} REDIS_URL=${REDIS_URL} JOB_MAX_RETRIES=${JOB_MAX_RETRIES} PYTHONPATH=.:src .venv/bin/python -m uvicorn apps.api.main:app --host ${API_HOST} --port ${API_PORT}" \
  > "${RUNTIME_DIR}/api.log" 2>&1 &
echo $! > "${RUNTIME_DIR}/api.pid"

nohup /bin/zsh -lc \
  "JOB_QUEUE_BACKEND=${JOB_QUEUE_BACKEND} REDIS_URL=${REDIS_URL} JOB_MAX_RETRIES=${JOB_MAX_RETRIES} PYTHONPATH=.:src .venv/bin/python -m apps.worker.runner" \
  > "${RUNTIME_DIR}/worker.log" 2>&1 &
echo $! > "${RUNTIME_DIR}/worker.pid"

nohup /bin/zsh -lc \
  "cd apps/web && NEXT_PUBLIC_API_BASE_URL=http://${API_HOST}:${API_PORT} npm run dev -- --hostname ${WEB_HOST} --port ${WEB_PORT}" \
  > "${RUNTIME_DIR}/web.log" 2>&1 &
echo $! > "${RUNTIME_DIR}/web.pid"

echo "API:  http://${API_HOST}:${API_PORT}"
echo "WEB:  http://${WEB_HOST}:${WEB_PORT}"
echo "Logs: ${RUNTIME_DIR}/api.log, ${RUNTIME_DIR}/worker.log, ${RUNTIME_DIR}/web.log"
