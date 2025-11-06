from datetime import datetime
from typing import Any
import re

def to_str(value):
    return str(value) if value is not None else None

def parse_date(value: Any):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except Exception:
        return None

def parse_datetime(value: Any):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None

def to_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt

def extract_note_number(note_title: str | None) -> int:
    """
    Extracts the numeric part from a note title string like:
    'Evaluation Note / Daily Note - 1' → 1
    'Daily Note - 12' → 12
    If no number found, defaults to 9999.
    """
    if not note_title:
        return 9999
    try:
        # Find the last number in the string (common HelloNote pattern)
        match = re.search(r"(\d+)\s*$", str(note_title).strip())
        if match:
            return int(match.group(1))
        else:
            return 9999
    except Exception:
        # Fallback if note_title is not a string or something unexpected
        return 9999


def map_hellonote_item_to_visit(item: dict) -> dict:
    return {
        "note_id": item.get("noteId"),
        "patient_id": item.get("patientId"),
        "first_name": item.get("patientFirstName"),
        "last_name": item.get("patientLastName"),
        "gender": item.get("gender"),
        "note": item.get("noteTitle"),
        "note_number": extract_note_number(item.get("noteTitle")),
        "case_description": item.get("caseTitle"),
        "case_date": to_naive(item.get("caseDate")),
        "primary_ins_id": to_str(item.get("primaryInsuranceId")),
        "primary_insurance": item.get("primaryInsuranceName"),
        "secondary_ins_id": to_str(item.get("secondaryInsuranceId")),
        "secondary_insurance": item.get("secondaryInsuranceName"),
        "note_date": to_naive(item.get("noteDate")),
        "referring_provider": item.get("referringPhysician"),
        "ref_provider_npi": to_str(item.get("npi")),
        "diagnosis": item.get("diagnosis"),
        "medical_diagnosis": item.get("medicalDiagnosis"),
        "finalized_date": to_naive(item.get("finalizedDate")),
        "pos": item.get("placeOfService"),
        "visit_type": item.get("visitType"),
        "attendance": item.get("attendance"),
        "comments": item.get("paymentTypeComment"),
        "supervising_therapist": None,
        "visiting_therapist": item.get("therapists"),
        "cpt_code": item.get("cptGCode"),
        "total_units": item.get("totalCptUnit"),
        "date_billed": to_naive(item.get("billedDate")),
        "billed_comment": item.get("billedComments"),
        "date_of_birth": to_naive(item.get("patientBirthday")),
        "patient_street1": item.get("patientStreet1Address"),
        "patient_street2": item.get("patientStreet2Address"),
        "patient_city": item.get("patientCityAddress"),
        "patient_state": item.get("patientStateAddress"),
        "patient_zip": item.get("patientZipAddress"),
        "case_type": item.get("caseType"),
        "location": item.get("caseOrganizationUnitName"),
        "hold": item.get("hold", False),
        "billed": item.get("billed", False),
        "paid": item.get("paid", False),
        "auth_number": to_str(item.get("authNumber")),
        "medical_record_no": to_str(item.get("medicalRecordId")),
        "rendering_provider_npi": to_str(item.get("renderingProviderNPI")),
        "case_id": item.get("caseId"),
        "time_in": to_naive(item.get("timeIn")),
        "time_out": to_naive(item.get("timeOut")),
        "visit_uid": None,
    }




def map_hellonote_list_to_visits(items: list[dict]) -> list[dict]:
    """Convert a HelloNote visit list to Visit row dicts."""
    return [map_hellonote_item_to_visit(i) for i in items]
