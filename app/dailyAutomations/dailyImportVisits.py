import os
import sys
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ✅ Fix Python path so imports work when run manually
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# ✅ Load .env explicitly (important for cron + manual run)
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(ENV_PATH)

from app.database import SessionLocal
from app.crud.visits_via_api import fetch_all_hellonote_visits
from app.crud.visits import insert_visit_rows
from app.helloNoteApi.visits_mapper import map_hellonote_list_to_visits
from app.powerAutomate.teamsMessageMyself import notify_teams


async def run_daily_import():
    stage = "daily_import_hellonote_visits"
    script_name = "dailyImportVisits.py"

    # ✅ Yesterday only
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    date_from = yesterday.strftime("%m/%d/%Y")
    date_to = yesterday.strftime("%m/%d/%Y")

    try:
        notify_teams("success", stage, f"Starting import for {date_from}", script_name)

        # ✅ 1. Fetch from HelloNote
        df = fetch_all_hellonote_visits(
            date_from=date_from,
            date_to=date_to,
            isAllStatus=True,
            isFinalizedDate=True,
            isAllStatusWithHold=False,
        )

        if df.empty:
            notify_teams("success", stage, f"No visits found ({date_from})", script_name)
            return

        # ✅ 2. Map DataFrame → rows
        hellonote_items = df.to_dict(orient="records")
        mapped_visits = map_hellonote_list_to_visits(hellonote_items)

        # ✅ 3. Insert to DB
        async with SessionLocal() as db:
            result = await insert_visit_rows(db, mapped_visits, uploaded_by=4)

        notify_teams(
            "success",
            stage,
            (
                f"✅ Daily Import Completed ({date_from})\n"
                f"- Inserted: {result['inserted_count']}\n"
                f"- Skipped: {result['skipped_count']}\n"
                f"- UIDs Created: {result['visit_uids_created']}"
            ),
            script_name,
        )

    except Exception as e:
        notify_teams("error", stage, f"Daily import failed: {e}", script_name)
        raise


if __name__ == "__main__":
    asyncio.run(run_daily_import())
