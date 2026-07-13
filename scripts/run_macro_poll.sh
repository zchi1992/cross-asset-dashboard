#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
LOCK_DIR="$PROJECT_DIR/state/macro_poll.lock"

mkdir -p "$PROJECT_DIR/state" "$PROJECT_DIR/logs"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') macro poll already running"
  exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT INT TERM

cd "$PROJECT_DIR"
if [ -n "${PYTHON_BIN:-}" ]; then
  "$PYTHON_BIN" macro.py poll once
elif [ -x "$PROJECT_DIR/.venv/bin/python3" ]; then
  "$PROJECT_DIR/.venv/bin/python3" macro.py poll once
elif command -v uv >/dev/null 2>&1; then
  uv run python macro.py poll once
else
  python3 macro.py poll once
fi
