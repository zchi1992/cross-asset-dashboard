#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
port="${1:-8765}"

cd "$repo_root"
export CROSS_ASSET_CONFIG_PATH="$repo_root/tests/fixtures/dashboard/config.json"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  exec "$PYTHON_BIN" -m uvicorn backend.app.main:app --host 127.0.0.1 --port "$port"
fi

if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port "$port"
fi

if command -v uv >/dev/null 2>&1; then
  exec uv run python -m uvicorn backend.app.main:app --host 127.0.0.1 --port "$port"
fi

exec python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port "$port"
