import os
import json
import math
import requests
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from app.helloNoteApi.transaction_report_request import fetch_hellonote_visits_raw, send_webhook


# -----------------------------------------------------------
# DB CONFIG
# -----------------------------------------------------------
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "payroll_tool"
DB_USER = "postgres"
DB_PASS = "Anchor2025"

SCRIPT_NAME = os.path.basename(__file__)

# Load webhook
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)
POWER_AUTOMATE_URL = os.getenv("POWER_AUTOMATE_URL")


# -----------------------------------------------------------
# Fetch ONLY HOLD visits, but keep all original arguments
# -----------------------------------------------------------
def fetch_hold_visits(
    date_from: str,
    date_to: str,
    isFinalizedDate: bool = False,
    isNoteDate: bool = False,
    isAllStatus: bool = False,
    isAllStatusWithHold: bool = False,
) -> pd.DataFrame:

    stage = "fetch_hold_visits"

    try:
        print(f"📄 Getting HOLD count for {date_from} - {date_to}...")

        # Always force HOLD = True (your requirement)
        preview = fetch_hellonote_visits_raw(
            dateFrom=date_from,
            dateTo=date_to,
            skipCount=0,
            amount=1,
            isHold=True,                 # 🔥 forced TRUE
            isFinalizedDate=isFinalizedDate,
            isNoteDate=isNoteDate,
            isAllStatus=isAllStatus,
            isAllStatusWithHold=isAllStatusWithHold,
        )

        total_count = preview.get("result", {}).get("totalCount", 0)
        if total_count == 0:
            print("⚠️ No HOLD records found.")
            send_webhook("success", stage, f"No HOLD records found for {date_from}-{date_to}.")
            return pd.DataFrame()

        print(f"✅ Found {total_count} HOLD visits.")
        send_webhook("success", stage, f"Found {total_count} HOLD visits to download.")

        master_list = []
        per_page = 25
        pages = math.ceil(total_count / per_page)

        for page in range(pages):
            skip = page * per_page
            print(f"➡️ Fetching page {page + 1}/{pages} (skip={skip})...")

            chunk = fetch_hellonote_visits_raw(
                dateFrom=date_from,
                dateTo=date_to,
                skipCount=skip,
                amount=per_page,
                isHold=True,                 # 🔥 forced TRUE on every page
                isFinalizedDate=isFinalizedDate,
                isNoteDate=isNoteDate,
                isAllStatus=isAllStatus,
                isAllStatusWithHold=isAllStatusWithHold,
            )

            items = chunk.get("result", {}).get("items", [])
            master_list.extend(items)

        df = pd.DataFrame(master_list)
        print(f"🧾 Final DataFrame shape: {df.shape}")
        send_webhook("success", stage, f"Downloaded {len(df)} HOLD visits.")

        return df

    except Exception as e:
        msg = f"Failed during {stage}: {e}"
        print(f"❌ {msg}")
        send_webhook("error", stage, msg)
        raise


# -----------------------------------------------------------
# Update DB: mark hold = TRUE by note_id
# -----------------------------------------------------------
def update_hold_flags(df: pd.DataFrame):
    if df.empty:
        print("No HOLD visits to update.")
        return

    print("🔧 Updating database HOLD flags...")

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    cur = conn.cursor()

    sql = """
        UPDATE visits
        SET hold = TRUE
        WHERE note_id = %s
    """

    updated = 0
    missing = 0

    for _, row in df.iterrows():
        note_id = row.get("noteId")
        if note_id is None:
            continue

        cur.execute(sql, (note_id,))
        if cur.rowcount > 0:
            updated += cur.rowcount
        else:
            missing += 1

    conn.commit()
    conn.close()

    print(f"✅ Updated {updated} visits.")
    if missing:
        print(f"⚠️ Missing {missing} visits (not found in hellonote_visits).")


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
if __name__ == "__main__":
    import sys

    # If arguments passed → use them
    if len(sys.argv) >= 3:
        date_from = sys.argv[1]
        date_to = sys.argv[2]
    else:
        # Fallback (optional)
        from datetime import datetime, timedelta
        today = datetime.now()
        last_30 = today - timedelta(days=30)
        date_from = last_30.strftime("%m/%d/%Y")
        date_to = today.strftime("%m/%d/%Y")

    print(f"Running HOLD sync for {date_from} - {date_to}")

    df = fetch_hold_visits(
        date_from=date_from,
        date_to=date_to,
        isFinalizedDate=False,
        isNoteDate=False,
        isAllStatus=False,
        isAllStatusWithHold=False,
    )

    update_hold_flags(df)
