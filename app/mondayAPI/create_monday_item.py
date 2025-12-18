import os
import json
import requests
from dotenv import load_dotenv

# -----------------------------------------------------------
# Load environment variables
# -----------------------------------------------------------
load_dotenv()

MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")  # Put this in .env

if not MONDAY_API_KEY:
    raise ValueError("❌ Missing MONDAY_API_KEY in .env file")

# -----------------------------------------------------------
# Load group map
# -----------------------------------------------------------
GROUP_MAP_PATH = os.path.join(os.path.dirname(__file__), "../mondayAPI/mondayImportGroup.json")

try:
    with open(GROUP_MAP_PATH, "r") as f:
        GROUP_MAP = json.load(f)
except FileNotFoundError:
    print(f"⚠️ group_map.json not found at {GROUP_MAP_PATH}, using empty map.")
    GROUP_MAP = {}


# -----------------------------------------------------------
# Function: create_monday_item
# -----------------------------------------------------------
def create_monday_item(
    group_name: str,
    therapist: str,
    note: str,
    case: str,
    case_id: int,
    patient_id: int,
    patient_display_id: str,
    first_name: str,
    last_name: str,
    cpt_code: str,
    note_date: str,
    note_id: int,
):
    """
    Create a new Monday.com item on board 18374251033.
    Automatically resolves `group_name` into a Monday group ID from group_map.json.
    """

    # 🔍 Translate friendly group name to actual Monday group_id
    group_id = GROUP_MAP.get(group_name)
    if not group_id:
        raise ValueError(f"❌ No mapping found for group '{group_name}' in {GROUP_MAP_PATH}")

    headers = {
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json",
    }

    column_values = {
        "text_mkxkn24e": note,
        "text_mkxkqkjk": f"{first_name} {last_name}",
        "text_mkxk7yyp": cpt_code,
        "date_mkxk3m38": note_date,
        "text_mkxkspta": case,
        "numeric_mkxkqm5j":note_id,
        "link_mkxk7vdh": {
            "url": f"https://emr.appv2.hellonote.com/app/main/patients/{patient_id}/cases/{case_id}/notes",
            "text": "Open Case",
        },
    }

    query = f"""
        mutation {{
        create_item(
            board_id: 18374251033,
            group_id: "{group_id}",
            item_name: "{therapist}",
            column_values: {json.dumps(json.dumps(column_values))}
        ) {{
            id
            name
        }}
    }}
    """


    response = requests.post(MONDAY_API_URL, headers=headers, json={"query": query})
    if response.status_code != 200:
        raise Exception(f"❌ Monday API request failed: {response.status_code} - {response.text}")

    data = response.json()
    if "errors" in data:
        raise Exception(f"⚠️ Monday returned error: {data['errors']}")

    item_info = data.get("data", {}).get("create_item", {})
    print(f"✅ Created item {item_info.get('id')} — {item_info.get('name')}")
    return item_info


# -----------------------------------------------------------
# Standalone test
# -----------------------------------------------------------
if __name__ == "__main__":
    test_group = "Duplicate Notes Detected"  # will map to "topics"
    create_monday_item(
        group_name=test_group,
        therapist="John Doe PT",
        note="Daily Note - 3",
        case="PT November 2025",
        case_id=365528,
        patient_id=293527,
        patient_display_id="251112368053",
        first_name="Mary",
        last_name="Johnson",
        cpt_code="97110(2),97116(1)",
        note_date="2025-11-11",
        note_id=987654,
    )
