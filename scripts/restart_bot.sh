#!/bin/zsh
set -euo pipefail

LABEL="com.george.stockrecommender.bot"
SCRIPT_DIR=${0:A:h}
REPO_ROOT=${SCRIPT_DIR:h}
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$REPO_ROOT/logs"

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if [ ! -f "$PLIST_PATH" ]; then
  echo "LaunchAgent is not installed: $PLIST_PATH"
  echo "Run ./scripts/install_launch_agent.sh first."
  exit 1
fi

cd "$REPO_ROOT"
mkdir -p "$LOG_DIR"

uv sync
uv run python manage.py migrate
launchctl kickstart -k "gui/$(id -u)/${LABEL}"

echo "Restarted ${LABEL}"
echo "Logs: tail -f ${LOG_DIR}/bot.out.log ${LOG_DIR}/bot.err.log"
