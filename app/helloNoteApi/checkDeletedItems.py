import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse

from sqlalchemy import false

# -----------------------------------------------------------
# CONFIG
# -----------------------------------------------------------
SCRIPT_NAME = os.path.basename(__file__)
BASE_DIR = os.path.dirname(__file__)

TOKEN_FILE = os.path.join(BASE_DIR, ".hellonote_token.json")

# Load .env (webhook + DB)
env_path = os.path.join(BASE_DIR, "../../.env")
load_dotenv(dotenv_path=env_path)

POWER_AUTOMATE_MYSELF = os.getenv("POWER_AUTOMATE_MYSELF")
DATABASE_URL = os.getenv("DATABASE_URL")  # REQUIRED for DB mode

# Compare key in HelloNote items
# Common candidates: "noteId", "id", "visitId"
HELLO_NOTE_ID_KEY = "noteId"

# Your DB column for the HelloNote visit identifier
DB_VISIT_ID_COLUMN = "note_id"

# Your DB date column to filter by (likely note_date)
DB_DATE_COLUMN = "note_date"

# Date range to pull from HelloNote + DB (MM/DD/YYYY)
DATE_FROM = "01/01/2026"
DATE_TO = "01/10/2026"

# Paging
PAGE_SIZE = 10000
MAX_PAGES = 200  # safety cap

# HelloNote request flags
IS_FINALIZED_DATE = False
IS_NOTE_DATE = False
IS_ALL_STATUS = False
IS_ALL_STATUS_WITH_HOLD = True
IS_HOLD = False


# -----------------------------------------------------------
# WEBHOOK
# -----------------------------------------------------------
def send_webhook(status: str, stage: str, message: str):
    if not POWER_AUTOMATE_MYSELF:
        print("⚠️ No POWER_AUTOMATE_MYSELF found in .env (skipping webhook)")
        return

    emoji = "✅" if status == "success" else "❌"
    full_message = f"{emoji} {SCRIPT_NAME}: {message}"
    payload = {"status": status, "stage": stage, "message": full_message}

    try:
        requests.post(POWER_AUTOMATE_MYSELF, json=payload, timeout=600)
        print(f"📤 Webhook sent ({status} @ {stage}) — {full_message}")
    except Exception as e:
        print(f"⚠️ Failed to send webhook: {e}")


# -----------------------------------------------------------
# TOKEN
# -----------------------------------------------------------
def load_token_from_file() -> dict:
    stage = "load_token"
    try:
        if not os.path.exists(TOKEN_FILE):
            raise FileNotFoundError(f"Token file not found: {TOKEN_FILE}")

        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)

        access_token = data.get("accessToken")
        if not access_token:
            raise ValueError("Token file does not contain 'accessToken'.")

        print(f"🔁 Loaded cached token for {data.get('userName', 'unknown user')}")
        return data

    except Exception as e:
        msg = f"Failed to load token: {e}"
        print(f"❌ {msg}")
        send_webhook("error", stage, msg)
        raise


# -----------------------------------------------------------
# HELLO NOTE FETCH (one page)
# -----------------------------------------------------------
def fetch_hellonote_visits_raw(
    dateFrom: str,
    dateTo: str,
    skipCount: int = 0,
    amount: int = 10000,
    isFinalizedDate: bool = False,
    isNoteDate: bool = False,
    isAllStatus: bool = False,
    isAllStatusWithHold: bool = True,
    isHold: bool = False,
) -> dict:
    stage = "fetch_visits"
    try:
        tokens = load_token_from_file()
        access_token = tokens["accessToken"]

        url = "https://emr.apiv2.hellonote.com/api/services/app/BillingTransactions/GetAll"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json, text/plain, */*",
        }

        payload = {
            "organizationUnitId": 1236,
            "insuranceId": None,
            "therapistId": None,
            "discipline": "",
            "isAllStatus": isAllStatus,
            "isAllStatusWithHold": isAllStatusWithHold,
            "dateFrom": dateFrom,
            "dateTo": dateTo,
            "isExcludeMedACases": True,
            "isFinalizedDate": isFinalizedDate,
            "isNoteDate": isNoteDate,
            "isHold": isHold,
            "caseTypeId": None,
            "sorting": "",
            "skipCount": skipCount,
            "maxResultCount": amount,
        }

        print(
            f"📡 Fetching HelloNote visits {dateFrom}..{dateTo} "
            f"(skip={skipCount}, limit={amount}, finalized={isFinalizedDate}, "
            f"noteDate={isNoteDate}, allStatus={isAllStatus}, withHold={isAllStatusWithHold})..."
        )

        response = requests.post(url, json=payload, headers=headers, timeout=600)

        if response.status_code == 401:
            raise PermissionError("Unauthorized: Token is expired or invalid.")

        response.raise_for_status()
        return response.json()

    except Exception as e:
        msg = f"Request failed during {stage}: {e}"
        print(f"❌ {msg}")
        send_webhook("error", stage, msg)
        raise


# -----------------------------------------------------------
# HELLO NOTE FETCH (all pages)
# -----------------------------------------------------------
def fetch_all_hellonote_visits_items(
    dateFrom: str,
    dateTo: str,
    page_size: int = 500,
    max_pages: int = 200,
    isFinalizedDate: bool = False,
    isNoteDate: bool = False,
    isAllStatus: bool = False,
    isAllStatusWithHold: bool = False,
    isHold: bool = False,
) -> list[dict]:
    stage = "fetch_all_pages"
    all_items: list[dict] = []
    skip = 0
    pages = 0

    while True:
        pages += 1
        if pages > max_pages:
            msg = f"Stopped after max_pages={max_pages} (safety). Pulled {len(all_items)} items so far."
            print(f"⚠️ {msg}")
            send_webhook("error", stage, msg)
            break

        raw = fetch_hellonote_visits_raw(
            dateFrom=dateFrom,
            dateTo=dateTo,
            skipCount=skip,
            amount=page_size,
            isFinalizedDate=isFinalizedDate,
            isNoteDate=isNoteDate,
            isAllStatus=isAllStatus,
            isAllStatusWithHold=isAllStatusWithHold,
            isHold=isHold,
        )

        result = raw.get("result") or {}
        items = result.get("items") or []

        all_items.extend(items)
        print(f"📄 Page {pages}: got {len(items)} items (total so far: {len(all_items)})")

        if not items or len(items) < page_size:
            break

        skip += page_size

    msg = f"Finished paging. Total items fetched: {len(all_items)}"
    print(f"✅ {msg}")
    send_webhook("success", stage, msg)
    return all_items


# -----------------------------------------------------------
# DB: expected IDs ONLY within DATE_FROM..DATE_TO using note_date
# -----------------------------------------------------------
def mmddyyyy_to_date(s: str):
    return datetime.strptime(s, "%m/%d/%Y").date()


def load_expected_ids_from_db_in_range(database_url: str, date_from_mmddyyyy: str, date_to_mmddyyyy: str) -> list[int]:
    """
    Pull expected visit IDs from visits table only for note_date within [DATE_FROM, DATE_TO].
    Implements:
      note_date >= DATE_FROM
      note_date <  (DATE_TO + 1 day)
    so DATE_TO is inclusive.
    """
    stage = "load_expected_ids_db"
    if not database_url:
        raise ValueError("DATABASE_URL missing.")

    try:
        import psycopg2  # type: ignore
    except Exception as ie:
        raise ImportError("psycopg2 is not installed. Install it.") from ie

    d_from = mmddyyyy_to_date(date_from_mmddyyyy)
    d_to = mmddyyyy_to_date(date_to_mmddyyyy)

    u = urlparse(database_url)
    conn = psycopg2.connect(
        dbname=u.path.lstrip("/"),
        user=u.username,
        password=u.password,
        host=u.hostname,
        port=u.port or 5432,
    )

    try:
        with conn.cursor() as cur:
            # Use DATE_TO inclusive by doing < (DATE_TO + interval '1 day')
            sql = f"""
                SELECT DISTINCT {DB_VISIT_ID_COLUMN}
                FROM visits
                WHERE {DB_VISIT_ID_COLUMN} IS NOT NULL
                  AND {DB_DATE_COLUMN} >= %s
                  AND {DB_DATE_COLUMN} < (%s::date + INTERVAL '1 day');
            """
            cur.execute(sql, (d_from, d_to))
            rows = cur.fetchall()
            ids = [int(r[0]) for r in rows if r and r[0] is not None]

        msg = f"Loaded {len(ids)} expected IDs from DB within {d_from}..{d_to} (inclusive)."
        print(f"✅ {msg}")
        send_webhook("success", stage, msg)
        return ids
    finally:
        conn.close()


# -----------------------------------------------------------
# COMPARE
# -----------------------------------------------------------
def extract_found_ids_from_hn_items(items: list[dict], id_key: str) -> set[int]:
    out: set[int] = set()
    for it in items:
        v = it.get(id_key)
        if v is None:
            continue
        s = str(v).strip()
        if s == "":
            continue
        try:
            out.add(int(s))
        except Exception:
            continue
    return out


def find_missing_ids(expected_ids: list[int], found_ids: set[int]) -> list[int]:
    expected_set = {int(x) for x in expected_ids if x is not None}
    return sorted(expected_set - found_ids)


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
if __name__ == "__main__":
    try:
        # 1) Load expected IDs from DB for the SAME date range
        expected_ids = load_expected_ids_from_db_in_range(DATABASE_URL, DATE_FROM, DATE_TO)
        if not expected_ids:
            raise ValueError("No expected IDs loaded for this date range; nothing to compare.")

        # 2) Fetch all HelloNote items for date range
        hn_items = fetch_all_hellonote_visits_items(
            dateFrom=DATE_FROM,
            dateTo=DATE_TO,
            page_size=PAGE_SIZE,
            max_pages=MAX_PAGES,
            isFinalizedDate=IS_FINALIZED_DATE,
            isNoteDate=IS_NOTE_DATE,
            isAllStatus=IS_ALL_STATUS,
            isAllStatusWithHold=IS_ALL_STATUS_WITH_HOLD,
            isHold=IS_HOLD,
        )

        print(f"✅ Total HelloNote items fetched: {len(hn_items)}")

        # 3) Extract found IDs from HelloNote payload
        found_ids = extract_found_ids_from_hn_items(hn_items, HELLO_NOTE_ID_KEY)

        # 4) Compare
        missing = find_missing_ids(expected_ids, found_ids)

        # 5) Report
        if not missing:
            msg = (
                f"Cross-check OK. Expected={len(expected_ids)} IDs (DB {DB_DATE_COLUMN} in {DATE_FROM}..{DATE_TO}); "
                f"Found={len(found_ids)} unique IDs in HelloNote; Missing=0. "
                f"Key='{HELLO_NOTE_ID_KEY}'."
            )
            print(f"✅ {msg}")
            send_webhook("success", "compare_ids", msg)
        else:
            msg = (
                f"Cross-check FAILED. Expected={len(expected_ids)} IDs (DB {DB_DATE_COLUMN} in {DATE_FROM}..{DATE_TO}); "
                f"Found={len(found_ids)} unique IDs in HelloNote; Missing={len(missing)}. "
                f"Key='{HELLO_NOTE_ID_KEY}'. First50={missing[:50]}"
            )
            print(f"❌ {msg}")
            print("\n=== MISSING VISIT IDS (full) ===")
            for mid in missing:
                print(mid)
            send_webhook("error", "compare_ids", msg)

    except Exception as e:
        msg = f"Unhandled error: {e}"
        print(f"❌ {msg}")
        send_webhook("error", "main", msg)
        raise
