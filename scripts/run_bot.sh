#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=${0:A:h}
REPO_ROOT=${SCRIPT_DIR:h}

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

UV_BIN="${UV_BIN:-$(command -v uv)}"

cd "$REPO_ROOT"
STARTED_AT=$(date "+%Y-%m-%d %H:%M:%S %z")
echo "[$STARTED_AT] ===== stock recommender bot starting ====="
echo "[$STARTED_AT] ===== stock recommender bot starting =====" >&2
exec "$UV_BIN" run python manage.py run_telegram_bot
