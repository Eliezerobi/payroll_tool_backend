import os
import requests
from dotenv import load_dotenv

# -----------------------------------------------------------
# Load env for POWER_AUTOMATE_DAILY_REPORT
# -----------------------------------------------------------
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)
POWER_AUTOMATE_DAILY_REPORT = os.getenv("POWER_AUTOMATE_DAILY_REPORT")


def notify_daily_report(message: str):
    """
    Send a simple message to the Daily Report webhook.

    Payload:
        { "message": "<text>" }
    """
    if not POWER_AUTOMATE_DAILY_REPORT:
        print("⚠️ POWER_AUTOMATE_DAILY_REPORT missing in .env — skipping.")
        return

    try:
        response = requests.post(
            POWER_AUTOMATE_DAILY_REPORT,
            json={"message": message},
            timeout=10
        )
        response.raise_for_status()
        print(f"📤 Daily report sent — {message}")
    except Exception as e:
        print(f"⚠️ Failed to send daily report: {e}")


# -----------------------------------------------------------
# Standalone Test Mode
# -----------------------------------------------------------
if __name__ == "__main__":
    print("✅ Testing DAILY REPORT bot...\n")

    test_script = os.path.basename(__file__)

    try:
        notify_daily_report(
            message="This is a test message for the Daily Report bot.",
        )
    except Exception as e:
        print(f"⚠️ Error sending test message: {e}")

    print("\n✅ Test complete. Check Teams / Power Automate.")
