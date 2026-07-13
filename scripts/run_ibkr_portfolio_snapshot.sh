#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
ENV_FILE="$PROJECT_DIR/state/ibkr.env"

if [ -f "$ENV_FILE" ]; then
  chmod 600 "$ENV_FILE"
  set -a
  . "$ENV_FILE"
  set +a
fi

hour="$(date '+%H')"
if [ "${IBKR_SYNC_SOURCE:-}" != "" ]; then
  source_name="$IBKR_SYNC_SOURCE"
elif [ "$hour" -ge 22 ]; then
  source_name="scheduled_2330"
else
  source_name="scheduled_2000"
fi

cd "$PROJECT_DIR"
if [ "${IBKR_PYTHON_BIN:-}" != "" ] && [ -x "$IBKR_PYTHON_BIN" ]; then
  exec "$IBKR_PYTHON_BIN" -m backend.app.portfolio_cli --source "$source_name" --lock-timeout 60
fi
if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
  exec "$PROJECT_DIR/.venv/bin/python" -m backend.app.portfolio_cli --source "$source_name" --lock-timeout 60
fi
if command -v uv >/dev/null 2>&1; then
  exec uv run python -m backend.app.portfolio_cli --source "$source_name" --lock-timeout 60
fi
exec python3 -m backend.app.portfolio_cli --source "$source_name" --lock-timeout 60
