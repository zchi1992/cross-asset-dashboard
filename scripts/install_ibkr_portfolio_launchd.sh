#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
IBKR_PYTHON_BIN="${IBKR_PYTHON_BIN:-$PROJECT_DIR/.venv/bin/python}"
CROSS_ASSET_CONFIG_PATH="${CROSS_ASSET_CONFIG_PATH:-$PROJECT_DIR/config.yaml}"
LABEL="com.chizhi.ibkr.portfolio-snapshot"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/$LABEL.plist"
PROJECT_DIR_XML="$(printf '%s\n' "$PROJECT_DIR" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')"
PYTHON_BIN_XML="$(printf '%s\n' "$IBKR_PYTHON_BIN" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')"
CONFIG_PATH_XML="$(printf '%s\n' "$CROSS_ASSET_CONFIG_PATH" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')"

mkdir -p "$TARGET_DIR" "$PROJECT_DIR/logs" "$PROJECT_DIR/state"
cat > "$TARGET_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PROJECT_DIR_XML/scripts/run_ibkr_portfolio_snapshot.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$PROJECT_DIR_XML</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>IBKR_PYTHON_BIN</key>
    <string>$PYTHON_BIN_XML</string>
    <key>CROSS_ASSET_CONFIG_PATH</key>
    <string>$CONFIG_PATH_XML</string>
  </dict>
  <key>StartCalendarInterval</key>
  <array>
    <dict>
      <key>Hour</key><integer>20</integer>
      <key>Minute</key><integer>0</integer>
    </dict>
    <dict>
      <key>Hour</key><integer>23</integer>
      <key>Minute</key><integer>30</integer>
    </dict>
  </array>
  <key>StandardOutPath</key>
  <string>$PROJECT_DIR_XML/logs/ibkr-portfolio-snapshot.out.log</string>
  <key>StandardErrorPath</key>
  <string>$PROJECT_DIR_XML/logs/ibkr-portfolio-snapshot.err.log</string>
</dict>
</plist>
PLIST
chmod 644 "$TARGET_PLIST"

launchctl bootout "gui/$(id -u)" "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$TARGET_PLIST"
launchctl enable "gui/$(id -u)/$LABEL"

echo "installed $LABEL"
echo "schedule: every day at 20:00 and 23:30 local time"
echo "config: $CROSS_ASSET_CONFIG_PATH"
