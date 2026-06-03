#!/bin/sh
set -eu

PROJECT_DIR="/Users/chizhi/Workspace/地平线数据收集"
LABEL="com.chizhi.zsxq.daily-poll"
SOURCE_PLIST="$PROJECT_DIR/launchd/$LABEL.plist"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/$LABEL.plist"

mkdir -p "$TARGET_DIR"
cp "$SOURCE_PLIST" "$TARGET_PLIST"
chmod 644 "$TARGET_PLIST"

launchctl bootout "gui/$(id -u)" "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$TARGET_PLIST"
launchctl enable "gui/$(id -u)/$LABEL"

echo "installed $LABEL"
echo "schedule: every weekday at 18:00 local time"
echo "logs: $PROJECT_DIR/logs/daily-poll.out.log and daily-poll.err.log"
