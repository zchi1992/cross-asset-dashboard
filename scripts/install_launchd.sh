#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LABEL="com.chizhi.zsxq.daily-poll"
SOURCE_PLIST="$PROJECT_DIR/launchd/$LABEL.plist"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/$LABEL.plist"
PROJECT_DIR_ESCAPED="$(printf '%s\n' "$PROJECT_DIR" | sed 's/[\/&]/\\&/g')"

mkdir -p "$TARGET_DIR" "$PROJECT_DIR/logs" "$PROJECT_DIR/state"
sed "s/__PROJECT_DIR__/$PROJECT_DIR_ESCAPED/g" "$SOURCE_PLIST" > "$TARGET_PLIST"
chmod 644 "$TARGET_PLIST"

launchctl bootout "gui/$(id -u)" "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$TARGET_PLIST"
launchctl enable "gui/$(id -u)/$LABEL"

echo "installed $LABEL"
echo "schedule: every weekday at 18:00 local time; polls every ~30 minutes until 23:00"
echo "logs: $PROJECT_DIR/logs/daily-poll.out.log and daily-poll.err.log"
