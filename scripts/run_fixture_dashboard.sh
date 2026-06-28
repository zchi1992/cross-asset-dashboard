#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
port="${1:-8765}"

cd "$repo_root"
export CROSS_ASSET_CONFIG_PATH="$repo_root/tests/fixtures/dashboard/config.json"

exec .venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port "$port"
