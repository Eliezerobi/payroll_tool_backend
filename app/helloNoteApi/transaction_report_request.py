import os
import json
import requests
from dotenv import load_dotenv

# -----------------------------------------------------------
# Configuration
# -----------------------------------------------------------
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".hellonote_token.json")

# Load .env (for webhook)
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)
POWER_AUTOMATE_URL = os.getenv("POWER_AUTOMATE_URL")

# Get current script name
SCRIPT_NAME = os.path.basename(__file__)


def send_webhook(status: str, stage: str, message: str):
    """Send message to Power Automate webhook with file name prefix and status emoji."""
    if not POWER_AUTOMATE_URL:
        print("⚠️ No POWER_AUTOMATE_URL found in .env (skipping webhook)")
        return

    emoji = "✅" if status == "success" else "❌"
    full_message = f"{emoji} {SCRIPT_NAME}: {message}"

    payload = {
        "status": status,
        "stage": stage,
        "message": full_message,
    }

    try:
        requests.post(POWER_AUTOMATE_URL, json=payload, timeout=10)
        print(f"📤 Webhook sent ({status} @ {stage}) — {full_message}")
    except Exception as e:
        print(f"⚠️ Failed to send webhook: {e}")


def load_token_from_file() -> dict:
    """Load cached HelloNote token from .hellonote_token.json."""
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


def fetch_hellonote_visits_raw(
    dateFrom: str,
    dateTo: str,
    skipCount: int = 0,
    amount: int = 10,
    isFinalizedDate: bool = False,
    isNoteDate: bool = False,
    isAllStatus: bool = False,
    isAllStatusWithHold: bool = False
) -> dict:
    """
    Fetch BillingTransactions from HelloNote using cached token.
    Args:
        dateFrom (str): Start date in MM/DD/YYYY format.
        dateTo (str): End date in MM/DD/YYYY format.
        skipCount (int): How many records to skip (for pagination).
        amount (int): Max number of records to fetch.
        isFinalizedDate (bool): Whether to filter by finalized date.
        isNoteDate (bool): Whether to filter by note date.
        isAllStatus (bool): Include all statuses.
        isAllStatusWithHold (bool): Include all statuses including held visits.
    """
    stage = "fetch_visits"
    try:
        tokens = load_token_from_file()
        access_token = tokens["accessToken"]

        url = "https://emr.apiv2.hellonote.com/api/services/app/BillingTransactions/GetAll"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json, text/plain, */*"
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
            "caseTypeId": None,
            "sorting": "",
            "skipCount": skipCount,
            "maxResultCount": amount
        }

        print(
            f"📡 Fetching HelloNote visits from {dateFrom} to {dateTo} "
            f"(skip={skipCount}, limit={amount}, finalized={isFinalizedDate}, "
            f"noteDate={isNoteDate}, allStatus={isAllStatus}, withHold={isAllStatusWithHold})..."
        )

        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 401:
            raise PermissionError("Unauthorized: Token is expired or invalid.")

        response.raise_for_status()

        try:
            raw_json = response.json()
            count = len(json.dumps(raw_json))
            msg = f"Retrieved {count} bytes of data successfully."
            print(f"✅ {msg}")
            send_webhook("success", stage, msg)
            return raw_json

        except Exception as e:
            msg = f"Could not parse JSON response: {e}"
            print(f"⚠️ {msg}")
            send_webhook("error", stage, msg)
            print(response.text[:2000])
            raise

    except Exception as e:
        msg = f"Request failed during {stage}: {e}"
        print(f"❌ {msg}")
        send_webhook("error", stage, msg)
        raise


# -----------------------------------------------------------
# Standalone mode
# -----------------------------------------------------------
if __name__ == "__main__":
    try:
        raw_data = fetch_hellonote_visits_raw(
            dateFrom="11/03/2025",
            dateTo="11/04/2025",
            skipCount=0,
            amount=5,
            isAllStatus=True,
        )
        print(json.dumps(raw_data, indent=2)[:4000])
    except Exception as e:
        msg = f"Unhandled error: {e}"
        print(f"❌ {msg}")
        send_webhook("error", "main", msg)
