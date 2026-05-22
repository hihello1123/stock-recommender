#!/bin/zsh
set -euo pipefail

LABEL="com.george.stockrecommender.bot"
SCRIPT_DIR=${0:A:h}
REPO_ROOT=${SCRIPT_DIR:h}
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$REPO_ROOT/logs"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
      <string>${REPO_ROOT}/scripts/run_bot.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>${REPO_ROOT}</string>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/bot.out.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/bot.err.log</string>
  </dict>
</plist>
PLIST

chmod +x "$REPO_ROOT/scripts/run_bot.sh"

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl enable "gui/$(id -u)/${LABEL}"
launchctl kickstart -k "gui/$(id -u)/${LABEL}"

echo "Installed and started ${LABEL}"
echo "Status: launchctl print gui/$(id -u)/${LABEL}"
echo "Logs: tail -f ${LOG_DIR}/bot.out.log ${LOG_DIR}/bot.err.log"
