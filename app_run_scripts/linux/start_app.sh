#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-5001}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="$ROOT_DIR/.venv"

if command -v ss >/dev/null 2>&1; then
  PORT_IN_USE="$(ss -ltn "sport = :$PORT" | awk 'NR > 1 {print $0}' || true)"
elif command -v lsof >/dev/null 2>&1; then
  PORT_IN_USE="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true)"
else
  PORT_IN_USE=""
fi

if [ -n "$PORT_IN_USE" ]; then
  echo "HomeHunter is already running on http://127.0.0.1:$PORT/"
  echo "Use app_run_scripts/linux/stop_app.sh first if you want to restart it."
  exit 0
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "Creating local Python environment in .venv..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" - <<'PY' >/dev/null 2>&1
import duckdb
import flask
import flask_cors
PY
then
  echo "Installing Python dependencies into .venv..."
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install -r requirements.txt
fi

echo "Starting HomeHunter at http://127.0.0.1:$PORT/"
exec "$VENV_DIR/bin/python" src/main/backend/app.py
