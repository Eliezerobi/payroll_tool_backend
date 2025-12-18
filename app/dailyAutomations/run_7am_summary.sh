#!/usr/bin/env bash
set -e

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(cd "$DIR/../.." && pwd)"

# Activate venv if exists
if [[ -f "$PROJECT_ROOT/venv/bin/activate" ]]; then
  source "$PROJECT_ROOT/venv/bin/activate"
fi

LOG_FILE="$DIR/reports_7am.log"

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') Running 7AM report summary ==="
  python3 -m app.dailyAutomations.reports_summary_7am
} >> "$LOG_FILE" 2>&1
