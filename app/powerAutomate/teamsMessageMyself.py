import os
import requests
from dotenv import load_dotenv
from datetime import datetime

# -----------------------------------------------------------
# Load environment variables (for POWER_AUTOMATE_MYSELF)
# -----------------------------------------------------------
env_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path=env_path)
POWER_AUTOMATE_MYSELF = os.getenv("POWER_AUTOMATE_MYSELF")


# -----------------------------------------------------------
# Function: notify_teams
# -----------------------------------------------------------
def notify_teams(status: str, stage: str, message: str, script_name: str = None):
    """
    Sends a notification to Microsoft Teams (via Power Automate webhook).

    Args:
        status (str): "success" or "error"
        stage (str): Step name, e.g. "fetch_visits", "insert_db"
        message (str): Message text to include
        script_name (str, optional): The name of the script sending this notification
    """
    if not POWER_AUTOMATE_MYSELF:
        print("⚠️ No POWER_AUTOMATE_MYSELF found in .env — skipping Teams notification.")
        return

    # Determine emoji for status
    emoji = "✅" if status.lower() == "success" else "❌"

    # Add timestamp and structure message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = f"{emoji} [{script_name}] " if script_name else emoji
    full_message = f"{prefix}{message}\n🕒 {timestamp}\n🔹 Stage: {stage}"

    payload = {
        "status": status,
        "stage": stage,
        "message": full_message,
    }

    try:
        response = requests.post(POWER_AUTOMATE_MYSELF, json=payload, timeout=10)
        response.raise_for_status()
        print(f"📤 Teams notified ({status} @ {stage}) — {full_message}")
    except Exception as e:
        print(f"⚠️ Failed to send Teams message: {e}")


# -----------------------------------------------------------
# Standalone Test Mode
# -----------------------------------------------------------
if __name__ == "__main__":
    """
    You can run this file directly to test Power Automate / Teams connection.
    Example:
        python3 app/utils/notify_teams.py
    """
    test_script = os.path.basename(__file__)

    print("🔧 Testing notify_teams function...\n")

    # Success test
    try:
        notify_teams(
            status="success",
            stage="test_success",
            message="This is a successful test message from notify_teams.py",
            script_name=test_script,
        )
    except Exception as e:
        print(f"⚠️ Error testing success message: {e}")

    # Error test
    try:
        notify_teams(
            status="error",
            stage="test_error",
            message="This is an error test message from notify_teams.py",
            script_name=test_script,
        )
    except Exception as e:
        print(f"⚠️ Error testing error message: {e}")

    print("\n✅ Test complete. Check your Teams channel for two messages (success + error).")
