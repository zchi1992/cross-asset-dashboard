#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
LOG_DIR="$PROJECT_DIR/logs"
STATE_DIR="$PROJECT_DIR/state"
LOCK_DIR="$STATE_DIR/daily_poll.lock"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-1800}"
POLL_WINDOW_START_HOUR="${POLL_WINDOW_START_HOUR:-18}"
POLL_WINDOW_END_HOUR="${POLL_WINDOW_END_HOUR:-23}"
MAX_RETRY_ATTEMPTS_PER_CYCLE="${MAX_RETRY_ATTEMPTS_PER_CYCLE:-3}"
WINDOW_START_SECONDS=$((POLL_WINDOW_START_HOUR * 3600))
WINDOW_END_SECONDS=$((POLL_WINDOW_END_HOUR * 3600))

mkdir -p "$LOG_DIR" "$STATE_DIR"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') another poll is already running"
  exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT INT TERM

cd "$PROJECT_DIR"

run_python() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    "$PYTHON_BIN" "$@"
    return
  fi
  if [ -x "$PROJECT_DIR/.venv/bin/python3" ]; then
    "$PROJECT_DIR/.venv/bin/python3" "$@"
    return
  fi
  if command -v uv >/dev/null 2>&1; then
    uv run python "$@"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 "$@"
    return
  fi
  echo "$(date '+%Y-%m-%d %H:%M:%S') no Python runtime found" >&2
  return 127
}

current_seconds_since_midnight() {
  date '+%H %M %S' | awk '{print ($1 * 3600) + ($2 * 60) + $3}'
}

within_poll_window() {
  now_seconds="$(current_seconds_since_midnight)"
  [ "$now_seconds" -ge "$WINDOW_START_SECONDS" ] && [ "$now_seconds" -le "$WINDOW_END_SECONDS" ]
}

seconds_until_window_end() {
  now_seconds="$(current_seconds_since_midnight)"
  remaining=$((WINDOW_END_SECONDS - now_seconds))
  if [ "$remaining" -lt 0 ]; then
    remaining=0
  fi
  printf '%s\n' "$remaining"
}

failed_download_count() {
  run_python -c 'import json, pathlib; path = pathlib.Path("state/downloads_manifest.json"); rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []; print(sum(1 for row in rows if str(row.get("status", "")).startswith("download_failed")))'
}

retry_delay_seconds() {
  run_python -c 'import random; print(random.randint(300, 600))'
}

retry_failed_downloads() {
  baseline_failed_count="${1:-0}"
  attempts=0
  FAILED_COUNT="$(failed_download_count)"
  if [ "$FAILED_COUNT" -le "$baseline_failed_count" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') failed_downloads=$FAILED_COUNT no_new_failed_downloads"
    return 0
  fi

  while [ "$FAILED_COUNT" -gt "$baseline_failed_count" ] && [ "$attempts" -lt "$MAX_RETRY_ATTEMPTS_PER_CYCLE" ]; do
    attempts=$((attempts + 1))
    DELAY_SECONDS="$(retry_delay_seconds)"
    remaining_seconds="$(seconds_until_window_end)"
    if [ "$remaining_seconds" -le "$DELAY_SECONDS" ]; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') failed_downloads=$FAILED_COUNT skip_retry_no_time_left"
      return 0
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') failed_downloads=$FAILED_COUNT retry_attempt=$attempts retry_in_seconds=$DELAY_SECONDS"
    sleep "$DELAY_SECONDS"

    echo "$(date '+%Y-%m-%d %H:%M:%S') start retry failed downloads"
    if run_python zsxq.py retry failed-downloads --min-delay-seconds 0 --max-delay-seconds 0; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') finish retry failed downloads"
    else
      echo "$(date '+%Y-%m-%d %H:%M:%S') retry failed downloads exited nonzero" >&2
      return 1
    fi

    FAILED_COUNT="$(failed_download_count)"
  done

  if [ "$FAILED_COUNT" -gt "$baseline_failed_count" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') failed_downloads=$FAILED_COUNT retry_limit_reached"
  else
    echo "$(date '+%Y-%m-%d %H:%M:%S') new failed downloads cleared"
  fi
}

run_poll_cycle() {
  INITIAL_FAILED_COUNT="$(failed_download_count)"
  echo "$(date '+%Y-%m-%d %H:%M:%S') start zsxq poll once"
  if run_python zsxq.py poll once; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') finish zsxq poll once"
  else
    echo "$(date '+%Y-%m-%d %H:%M:%S') zsxq poll once exited nonzero" >&2
    return 1
  fi
  retry_failed_downloads "$INITIAL_FAILED_COUNT"
}

sleep_until_next_cycle() {
  remaining_seconds="$(seconds_until_window_end)"
  if [ "$remaining_seconds" -le 0 ]; then
    return 1
  fi
  sleep_seconds="$POLL_INTERVAL_SECONDS"
  if [ "$sleep_seconds" -gt "$remaining_seconds" ]; then
    sleep_seconds="$remaining_seconds"
  fi
  echo "$(date '+%Y-%m-%d %H:%M:%S') next_poll_in_seconds=$sleep_seconds"
  sleep "$sleep_seconds"
}

if ! within_poll_window; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') outside polling window ${POLL_WINDOW_START_HOUR}:00-${POLL_WINDOW_END_HOUR}:00"
  exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') enter polling window ${POLL_WINDOW_START_HOUR}:00-${POLL_WINDOW_END_HOUR}:00 interval_seconds=$POLL_INTERVAL_SECONDS"
while within_poll_window; do
  if ! run_poll_cycle; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') poll cycle failed; continuing until window closes" >&2
  fi
  sleep_until_next_cycle || break
done
echo "$(date '+%Y-%m-%d %H:%M:%S') leave polling window"
