#!/bin/sh
set -eu

PROJECT_DIR="/Users/chizhi/Workspace/地平线数据收集"
LOG_DIR="$PROJECT_DIR/logs"
LOCK_DIR="$PROJECT_DIR/state/daily_poll.lock"

mkdir -p "$LOG_DIR" "$PROJECT_DIR/state"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') another poll is already running"
  exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT INT TERM

cd "$PROJECT_DIR"

if [ -x "$PROJECT_DIR/.venv/bin/python3" ]; then
  PYTHON="$PROJECT_DIR/.venv/bin/python3"
else
  PYTHON="/usr/bin/python3"
fi

failed_download_count() {
  "$PYTHON" -c 'import json, pathlib; path = pathlib.Path("state/downloads_manifest.json"); rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []; print(sum(1 for row in rows if str(row.get("status", "")).startswith("download_failed")))'
}

retry_delay_seconds() {
  "$PYTHON" -c 'import random; print(random.randint(300, 600))'
}

echo "$(date '+%Y-%m-%d %H:%M:%S') start zsxq poll once"
"$PYTHON" zsxq.py poll once
echo "$(date '+%Y-%m-%d %H:%M:%S') finish zsxq poll once"

FAILED_COUNT="$(failed_download_count)"
while [ "$FAILED_COUNT" -gt 0 ]; do
  DELAY_SECONDS="$(retry_delay_seconds)"
  echo "$(date '+%Y-%m-%d %H:%M:%S') failed_downloads=$FAILED_COUNT retry_in_seconds=$DELAY_SECONDS"
  sleep "$DELAY_SECONDS"

  echo "$(date '+%Y-%m-%d %H:%M:%S') start retry failed downloads"
  "$PYTHON" zsxq.py retry failed-downloads --min-delay-seconds 0 --max-delay-seconds 0
  echo "$(date '+%Y-%m-%d %H:%M:%S') finish retry failed downloads"

  FAILED_COUNT="$(failed_download_count)"
done

echo "$(date '+%Y-%m-%d %H:%M:%S') all downloads succeeded"
