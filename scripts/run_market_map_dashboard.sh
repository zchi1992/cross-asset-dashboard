#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -x ".venv/bin/uvicorn" ]; then
  echo "Missing .venv/bin/uvicorn. Run: python3 -m venv .venv && .venv/bin/python3 -m pip install -r requirements.txt"
  exit 1
fi

if [ ! -d "frontend/dist" ]; then
  echo "Missing frontend/dist. Run: cd frontend && npm install && npm run build"
  exit 1
fi

exec .venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
