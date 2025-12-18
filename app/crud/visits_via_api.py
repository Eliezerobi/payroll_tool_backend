import os
import json
import math
import requests
import pandas as pd
from dotenv import load_dotenv
from app.helloNoteApi.transaction_report_request import fetch_hellonote_visits_raw, send_webhook

# -----------------------------------------------------------
# Configuration
# -----------------------------------------------------------
SCRIPT_NAME = os.path.basename(__file__)

# Load webhook for optional notifications
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)
POWER_AUTOMATE_URL = os.getenv("POWER_AUTOMATE_URL")


def fetch_all_hellonote_visits(
    date_from: str,
    date_to: str,
    isFinalizedDate: bool = False,
    isNoteDate: bool = False,
    isAllStatus: bool = False,
    isHold: bool = False,
    isAllStatusWithHold: bool = False,
) -> pd.DataFrame:
    """
    Fetch all HelloNote BillingTransactions between two dates, automatically paginated.
    Returns a single pandas DataFrame containing all rows.
    """

    stage = "fetch_all"
    try:
        # 1️⃣ Get total count using limit=1
        print(f"📄 Getting total count from HelloNote ({date_from} - {date_to})...")
        preview = fetch_hellonote_visits_raw(
            dateFrom=date_from,
            dateTo=date_to,
            skipCount=0,
            amount=1,
            isFinalizedDate=isFinalizedDate,
            isNoteDate=isNoteDate,
            isAllStatus=isAllStatus,
            isAllStatusWithHold=isAllStatusWithHold,
        )

        total_count = preview.get("result", {}).get("totalCount", 0)
        if total_count == 0:
            print("⚠️ No records found.")
            send_webhook("success", stage, f"No records found for range {date_from} - {date_to}.")
            return pd.DataFrame()

        print(f"✅ Found {total_count} total records.")
        send_webhook("success", stage, f"Found {total_count} total records to download.")

        # 2️⃣ Loop through in chunks of 25
        master_list = []
        per_page = 25
        pages = math.ceil(total_count / per_page)

        for page in range(pages):
            skip = page * per_page
            print(f"➡️ Fetching page {page + 1}/{pages} (skip={skip})...")

            data_chunk = fetch_hellonote_visits_raw(
                dateFrom=date_from,
                dateTo=date_to,
                skipCount=skip,
                amount=per_page,
                isFinalizedDate=isFinalizedDate,
                isNoteDate=isNoteDate,
                isAllStatus=isAllStatus,
                isAllStatusWithHold=isAllStatusWithHold,
            )

            items = data_chunk.get("result", {}).get("items", [])
            if not items:
                print(f"⚠️ No items in page {page + 1}")
                continue

            master_list.extend(items)

        print(f"✅ Completed: collected {len(master_list)} records total.")
        send_webhook("success", stage, f"Collected {len(master_list)} records total.")

        # 3️⃣ Convert to DataFrame
        df = pd.DataFrame(master_list)
        print(f"🧾 Final DataFrame shape: {df.shape}")

        return df

    except Exception as e:
        msg = f"Failed during {stage}: {e}"
        print(f"❌ {msg}")
        send_webhook("error", stage, msg)
        raise


# -----------------------------------------------------------
# Standalone execution
# -----------------------------------------------------------
if __name__ == "__main__":
    try:
        df = fetch_all_hellonote_visits(
            date_from="11/01/2025",
            date_to="11/04/2025",
            isAllStatus=True,
            isFinalizedDate=True,
        )

        print(df.head())
        print(f"✅ Download complete — {len(df)} rows total.")

    except Exception as e:
        msg = f"Unhandled error in {SCRIPT_NAME}: {e}"
        print(f"❌ {msg}")
        send_webhook("error", "main", msg)
