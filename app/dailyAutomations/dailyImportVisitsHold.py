import os
import sys
import asyncio
import subprocess
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ---------------------------------------------------------
# Fix Python path for manual + cron runs
# ---------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# Load .env explicitly
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(ENV_PATH)

from app.powerAutomate.teamsMessageMyself import notify_teams


async def run_daily_hold_update():
    stage = "daily_hold_update"
    script_name = "dailyHoldUpdate.py"

    # Yesterday only
    today = datetime.now()
    fullMonth = today - timedelta(days=45)
    date_from = fullMonth.strftime("%m/%d/%Y")
    date_to = today.strftime("%m/%d/%Y")

    try:
        # ---------------------------------------------------------
        # Notify start
        # ---------------------------------------------------------
        notify_teams(
            "success",
            stage,
            f"Starting HOLD update for {date_from}",
            script_name,
        )

        # ---------------------------------------------------------
        # RUN HOLD SYNC SCRIPT
        # python3 -m app.crud.hold_via_api
        # ---------------------------------------------------------
        notify_teams("success", stage, "Running HOLD sync…", script_name)

        subprocess.run(
            [
                "python3",
                "-m",
                "app.crud.hold_via_api",
                date_from,
                date_to,
            ],
            cwd=PROJECT_ROOT,
            check=True,
        )

        # ---------------------------------------------------------
        # Notify completion
        # ---------------------------------------------------------
        notify_teams(
            "success",
            stage,
            f"✅ HOLD Update Completed ({date_from})",
            script_name,
        )

    except Exception as e:
        notify_teams("error", stage, f"HOLD update failed: {e}", script_name)
        raise


if __name__ == "__main__":
    asyncio.run(run_daily_hold_update())
