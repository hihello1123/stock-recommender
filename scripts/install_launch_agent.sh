#!/bin/zsh
set -euo pipefail

BOT_LABEL="com.george.stockrecommender.bot"
WORKER_LABEL="com.george.stockrecommender.worker"
SCRIPT_DIR=${0:A:h}
REPO_ROOT=${SCRIPT_DIR:h}
BOT_PLIST_PATH="$HOME/Library/LaunchAgents/${BOT_LABEL}.plist"
WORKER_PLIST_PATH="$HOME/Library/LaunchAgents/${WORKER_LABEL}.plist"
LOG_DIR="$REPO_ROOT/logs"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

cat > "$BOT_PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${BOT_LABEL}</string>
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

cat > "$WORKER_PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${WORKER_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
      <string>${REPO_ROOT}/scripts/run_worker.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>${REPO_ROOT}</string>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/worker.out.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/worker.err.log</string>
  </dict>
</plist>
PLIST

chmod +x "$REPO_ROOT/scripts/run_bot.sh" "$REPO_ROOT/scripts/run_worker.sh"

install_agent() {
  local LABEL="$1"
  local PLIST_PATH="$2"
  launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
  launchctl enable "gui/$(id -u)/${LABEL}"
  launchctl kickstart -k "gui/$(id -u)/${LABEL}"
  echo "Installed and started ${LABEL}"
  echo "Status: launchctl print gui/$(id -u)/${LABEL}"
}

install_agent "$BOT_LABEL" "$BOT_PLIST_PATH"
install_agent "$WORKER_LABEL" "$WORKER_PLIST_PATH"

echo "Logs: tail -f ${LOG_DIR}/bot.out.log ${LOG_DIR}/bot.err.log ${LOG_DIR}/worker.out.log ${LOG_DIR}/worker.err.log"
