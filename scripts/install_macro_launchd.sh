#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LABEL="com.chizhi.cross-asset-dashboard.macro-poll"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/$LABEL.plist"
PROJECT_DIR_XML="$(printf '%s\n' "$PROJECT_DIR" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')"

mkdir -p "$TARGET_DIR" "$PROJECT_DIR/logs" "$PROJECT_DIR/state"
cat > "$TARGET_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$PROJECT_DIR_XML/scripts/run_macro_poll.sh</string></array>
  <key>WorkingDirectory</key><string>$PROJECT_DIR_XML</string>
  <key>StartCalendarInterval</key><array>
    <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>30</integer></dict>
  </array>
  <key>StandardOutPath</key><string>$PROJECT_DIR_XML/logs/macro-poll.out.log</string>
  <key>StandardErrorPath</key><string>$PROJECT_DIR_XML/logs/macro-poll.err.log</string>
</dict></plist>
PLIST
chmod 644 "$TARGET_PLIST"
launchctl bootout "gui/$(id -u)" "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$TARGET_PLIST"
launchctl enable "gui/$(id -u)/$LABEL"
echo "installed $LABEL at 09:00 and 20:30 local time"
