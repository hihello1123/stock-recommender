#!/bin/zsh
set -euo pipefail

BOT_LABEL="com.george.stockrecommender.bot"
WORKER_LABEL="com.george.stockrecommender.worker"
SCRIPT_DIR=${0:A:h}
REPO_ROOT=${SCRIPT_DIR:h}
BOT_PLIST_PATH="$HOME/Library/LaunchAgents/${BOT_LABEL}.plist"
WORKER_PLIST_PATH="$HOME/Library/LaunchAgents/${WORKER_LABEL}.plist"
LOG_DIR="$REPO_ROOT/logs"

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if [ ! -f "$BOT_PLIST_PATH" ] || [ ! -f "$WORKER_PLIST_PATH" ]; then
  echo "LaunchAgent is not installed."
  echo "Run ./scripts/install_launch_agent.sh first."
  exit 1
fi

cd "$REPO_ROOT"
mkdir -p "$LOG_DIR"

uv sync
uv run python manage.py migrate
launchctl kickstart -k "gui/$(id -u)/${BOT_LABEL}"
launchctl kickstart -k "gui/$(id -u)/${WORKER_LABEL}"

echo "Restarted ${BOT_LABEL}"
echo "Restarted ${WORKER_LABEL}"
echo "Logs: tail -f ${LOG_DIR}/bot.out.log ${LOG_DIR}/bot.err.log ${LOG_DIR}/worker.out.log ${LOG_DIR}/worker.err.log"
