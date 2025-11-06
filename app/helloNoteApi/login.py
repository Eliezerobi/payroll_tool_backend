import os
import json
import requests
from dotenv import load_dotenv

def hellonote_login() -> dict:
    """
    Logs in to HelloNote EMR using credentials from .env (two folders up)
    and notifies a Power Automate webhook on success or failure.
    """

    # -----------------------------------------------------------------
    # 1️⃣ Load .env
    # -----------------------------------------------------------------
    env_path = os.path.join(os.path.dirname(__file__), "../../.env")
    load_dotenv(dotenv_path=env_path)

    EMAIL = os.getenv("HELLONOTE_EMAIL")
    PASSWORD = os.getenv("HELLONOTE_PASSWORD")
    POWER_AUTOMATE_URL = os.getenv("POWER_AUTOMATE_URL")

    if not EMAIL or not PASSWORD:
        raise Exception(f"Missing HELLONOTE_EMAIL or HELLONOTE_PASSWORD in {env_path}")
    if not POWER_AUTOMATE_URL:
        raise Exception(f"Missing POWER_AUTOMATE_URL in {env_path}")

    # -----------------------------------------------------------------
    # 2️⃣ Build request body and headers
    # -----------------------------------------------------------------
    BASE_URL = "https://emr.apiv2.hellonote.com/api"
    LOGIN_URL = f"{BASE_URL}/TokenAuth/Authenticate"

    payload = {
        "userNameOrEmailAddress": EMAIL,
        "password": PASSWORD,
        "rememberClient": False,
        "singleSignIn": False,
        "returnUrl": None,
        "captchaResponse": None
    }

    body = json.dumps(payload).encode("utf-8")

    headers = {
        "Host": "emr.apiv2.hellonote.com",
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
    }

    # -----------------------------------------------------------------
    # 3️⃣ Attempt login
    # -----------------------------------------------------------------
    try:
        print("🔐 Logging in to HelloNote...")
        response = requests.post(LOGIN_URL, data=body, headers=headers)
        response.raise_for_status()

        data = response.json()
        if not data.get("success"):
            raise Exception(f"❌ Login failed: {data}")

        result = data["result"]
        print(f"✅ Logged in as {result['userName']}")

        # -----------------------------------------------------------------
        # 4️⃣ Notify Power Automate (success)
        # -----------------------------------------------------------------
        success_payload = {
            "status": "success",
            "message": f"Logged in successfully as {result['userName']}",
            "token_valid_hours": result["expireInSeconds"] / 3600
        }
        requests.post(POWER_AUTOMATE_URL, json=success_payload, timeout=10)
        print("📤 Success notification sent to Power Automate.")
        
        return result

    except Exception as e:
        error_message = str(e)
        print(f"❌ Error: {error_message}")

        # -----------------------------------------------------------------
        # 5️⃣ Notify Power Automate (failure)
        # -----------------------------------------------------------------
        try:
            fail_payload = {
                "status": "error",
                "message": error_message
            }
            requests.post(POWER_AUTOMATE_URL, json=fail_payload, timeout=10)
            print("📤 Error notification sent to Power Automate.")
        except Exception as notify_err:
            print(f"⚠️ Could not notify Power Automate: {notify_err}")

        raise  # re-raise error to stop script if needed


if __name__ == "__main__":
    hellonote_login()
