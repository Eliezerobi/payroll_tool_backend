import os
import json
import time
import requests
from dotenv import load_dotenv

CACHE_FILE = os.path.join(os.path.dirname(__file__), ".hellonote_token.json")


def load_cached_token():
    """Load token from cache if it exists and is still valid."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        if time.time() < data.get("expires_at", 0):
            return data  # still valid
    except Exception:
        pass
    return None


def save_token_to_cache(result):
    """Save token with expiry time (now + expireInSeconds)."""
    data = {
        "userName": result["userName"],
        "accessToken": result["accessToken"],
        "refreshToken": result["refreshToken"],
        "expires_at": time.time() + result["expireInSeconds"] - 60,  # 1 min buffer
    }
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)
    return data


def hellonote_login() -> dict:
    """Log in to HelloNote or use cached token if valid."""

    # 1️⃣ Load cached token if still valid
    cached = load_cached_token()
    if cached:
        print(f"✅ Using cached token for {cached['userName']}")
        return cached

    # 2️⃣ Load env variables
    env_path = os.path.join(os.path.dirname(__file__), "../../.env")
    load_dotenv(dotenv_path=env_path)

    EMAIL = os.getenv("HELLONOTE_EMAIL")
    PASSWORD = os.getenv("HELLONOTE_PASSWORD")
    POWER_AUTOMATE_MYSELF = os.getenv("POWER_AUTOMATE_MYSELF")

    if not EMAIL or not PASSWORD:
        raise Exception(f"Missing HELLONOTE_EMAIL or HELLONOTE_PASSWORD in {env_path}")

    # 3️⃣ Build request
    LOGIN_URL = "https://emr.apiv2.hellonote.com/api/TokenAuth/Authenticate"
    payload = {
        "userNameOrEmailAddress": EMAIL,
        "password": PASSWORD,
        "rememberClient": False,
        "singleSignIn": False,
        "returnUrl": None,
        "captchaResponse": None,
    }

    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Host": "emr.apiv2.hellonote.com",
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
    }

    print("🔐 Logging in to HelloNote...")
    try:
        response = requests.post(LOGIN_URL, data=body, headers=headers)
        response.raise_for_status()
        data = response.json()
        result = data["result"]
        print(f"✅ Logged in as {result['userName']}")

        # save new token
        token_data = save_token_to_cache(result)

        # Notify Power Automate (optional)
        if POWER_AUTOMATE_MYSELF:
            try:
                requests.post(POWER_AUTOMATE_MYSELF, json={
                    "status": "success",
                    "message": f"New HelloNote token acquired for {result['userName']}"
                }, timeout=10)
            except Exception:
                pass

        return token_data

    except Exception as e:
        err = str(e)
        print("❌ Login failed:", err)
        if POWER_AUTOMATE_MYSELF:
            try:
                requests.post(POWER_AUTOMATE_MYSELF, json={"status": "error", "message": err}, timeout=10)
            except Exception:
                pass
        raise


if __name__ == "__main__":
    token = hellonote_login()
    print("\n🔑 Access Token:", token["accessToken"][:50], "...")
