#!/bin/sh
set -eu

LABEL="com.chizhi.cross-asset-dashboard.macro-poll"
TARGET_PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
launchctl bootout "gui/$(id -u)" "$TARGET_PLIST" >/dev/null 2>&1 || true
rm -f "$TARGET_PLIST"
echo "uninstalled $LABEL"
