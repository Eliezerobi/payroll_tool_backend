#!/usr/bin/env bash
set -euo pipefail

# Paths
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(cd "$DIR/../.." && pwd)"
LOG_DIR="$DIR/logs"
mkdir -p "$LOG_DIR"

# Activate venv
if [[ -f "$PROJECT_ROOT/venv/bin/activate" ]]; then
  source "$PROJECT_ROOT/venv/bin/activate"
fi

# Timestamp
ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "$(ts) === Running daily master ===" | tee -a "$LOG_DIR/master.log"


# ---------------------------------------------------------
# 1. Run daily login (must succeed)
# ---------------------------------------------------------
echo "$(ts) --- Running dailyLogin.py ---" | tee -a "$LOG_DIR/master.log"
if ! /usr/bin/python3 "$DIR/dailyLogin.py" >> "$LOG_DIR/login.log" 2>&1; then
  echo "$(ts) ❌ dailyLogin.py FAILED — stopping" | tee -a "$LOG_DIR/master.log"
  exit 1
fi


# ---------------------------------------------------------
# 2. Run daily import (main visit import)
# ---------------------------------------------------------
echo "$(ts) --- Running dailyImportVisits.py ---" | tee -a "$LOG_DIR/master.log"
if ! /usr/bin/python3 "$DIR/dailyImportVisits.py" >> "$LOG_DIR/import.log" 2>&1; then
  echo "$(ts) ❌ dailyImportVisits.py FAILED — stopping" | tee -a "$LOG_DIR/master.log"
  exit 1
fi


# ---------------------------------------------------------
# 3. Run HOLD update AFTER import, BEFORE reports
# ---------------------------------------------------------
echo "$(ts) --- Running dailyImportVisitsHold.py ---" | tee -a "$LOG_DIR/master.log"
if ! /usr/bin/python3 "$DIR/dailyImportVisitsHold.py" >> "$LOG_DIR/hold.log" 2>&1; then
  echo "$(ts) ❌ dailyImportVisitsHold.py FAILED — stopping" | tee -a "$LOG_DIR/master.log"
  exit 1
fi


# ---------------------------------------------------------
# 4. Run daily reports
# ---------------------------------------------------------
echo "$(ts) --- Running dailyReports ---" | tee -a "$LOG_DIR/master.log"
cd "$PROJECT_ROOT"

echo "$(ts) --- Running dailyReports (module) ---" | tee -a "$LOG_DIR/master.log"
if ! /usr/bin/python3 -m app.dailyAutomations.dailyReports >> "$LOG_DIR/reports.log" 2>&1; then
  echo "$(ts) ❌ dailyReports FAILED" | tee -a "$LOG_DIR/master.log"
  exit 1
fi


# ---------------------------------------------------------
# 5. Run reports_summary_7am AFTER reports succeed
# ---------------------------------------------------------
echo "$(ts) --- Running reports_summary_7am ---" | tee -a "$LOG_DIR/master.log"

if ! /usr/bin/python3 -m app.dailyAutomations.reports_summary_7am >> "$LOG_DIR/summary7am.log" 2>&1; then
  echo "$(ts) ❌ reports_summary_7am FAILED" | tee -a "$LOG_DIR/master.log"
  exit 1
fi

echo "$(ts) ✅ reports_summary_7am finished successfully" | tee -a "$LOG_DIR/master.log"
echo "$(ts) ✅ All daily tasks finished successfully" | tee -a "$LOG_DIR/master.log"
