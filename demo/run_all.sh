#!/usr/bin/env bash
# SEABeacon Demo 2 — launch all backends + frontend (macOS / Linux / Git-Bash)
#
# Starts the three AI daemons in the background, then the Vite dev server in the
# foreground. Ctrl-C stops the dev server and kills the backgrounded daemons.
# Assumes each backend's .env and frontend/.env are configured and dependencies
# are installed (see README.md).
#
# Usage:  ./run_all.sh

set -euo pipefail
DEMO2="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHASE1="$(dirname "$DEMO2")"
PY="${PYTHON:-python}"

pids=()
start_daemon() {
  local name="$1" dir="$2"; shift 2
  if [ ! -d "$dir" ]; then
    echo "Skipping $name — directory not found: $dir" >&2
    return
  fi
  echo ">> Starting $name"
  ( cd "$dir" && exec "$@" ) &
  pids+=("$!")
}

cleanup() {
  echo ""
  echo ">> Stopping backends..."
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

# ── Backends (background) ─────────────────────────────────────────────────────
start_daemon "AI-1 Flood (LSTM)"  "$PHASE1/lstm_model"              "$PY" main.py
start_daemon "AI-2 Typhoon (XGB)" "$PHASE1/xgboost_forecast/automation" "$PY" daemon.py
start_daemon "AI-3 Social (NLP)"  "$PHASE1/nlp_analysis"            "$PY" main.py

# ── Frontend (foreground) ─────────────────────────────────────────────────────
echo ">> Starting frontend (Vite dev server)"
cd "$DEMO2/frontend"
npm run dev
