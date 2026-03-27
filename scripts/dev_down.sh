#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${ROOT_DIR}/.runtime"

for name in api worker web; do
  pid_file="${RUNTIME_DIR}/${name}.pid"
  if [ -f "${pid_file}" ]; then
    pid="$(cat "${pid_file}")"
    kill "${pid}" >/dev/null 2>&1 || true
    rm -f "${pid_file}"
    echo "stopped ${name} (${pid})"
  else
    echo "skip ${name} (no pid file)"
  fi
done
