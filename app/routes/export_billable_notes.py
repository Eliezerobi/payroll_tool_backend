import re
import json
from collections import defaultdict
from io import BytesIO
from datetime import date
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.visits import Visit
from app.models.patients import Patient
from app.dependencies.auth import get_current_user
from app.models.users import User

router = APIRouter()

# ------------------ CPT PARSER ------------------ #
def parse_cpt_string(cpt_str: str):
    """
    Parse a CPT column value into structured rows.
    Each CPT code gets its own row, with units and modifiers applied.
    """
    if not cpt_str or not isinstance(cpt_str, str):
        return []

    parts = cpt_str.split(":")
    modifiers = []
    discipline = None

    # Identify discipline (GP, GO, GN)
    if parts[0] in {"GP", "GO", "GN"}:
        discipline = parts[0]
        modifiers = parts[1:]
    else:
        modifiers = parts

    # Separate CPT codes from modifiers
    cpt_part = ""
    for i, m in enumerate(modifiers):
        if re.search(r"\d{5}\(\d+\)", m):  # CPT code pattern
            cpt_part = ":".join(modifiers[i:])
            modifiers = modifiers[:i]
            break

    # Clean modifiers
    mod_flags = {"59": "59", "CQ": "CQ", "KX": "KX", "CO": "CO"}
    applied_mods = {k: (k in modifiers) for k in mod_flags}

    # Extract CPT + units
    cpt_matches = re.findall(r"(\d{5})\((\d+)\)", cpt_part)
    cpt_units = defaultdict(int)
    for code, units in cpt_matches:
        cpt_units[code] += int(units)

    # Build output rows
    rows = []
    for code, units in cpt_units.items():
        rows.append({
            "cpt_code": code,
            "total_units": units,
            "modifier_specialty": discipline,
            "modifier_59": "59" if applied_mods["59"] else None,
            "modifier_cq": "CQ" if applied_mods["CQ"] else None,
            "modifier_kx": "KX" if applied_mods["KX"] else None,
            "modifier_co": "CO" if applied_mods["CO"] else None,
        })

    return rows

def to_str_or_none(x: Any, keep_commas: bool = False) -> str | None:
    """Convert values to string or None, optionally keeping commas."""
    if x is None:
        return None
    if isinstance(x, float) and pd.isna(x):
        return None
    s = str(x).strip()
    if s.lower() in {"", "nan", "nat", "none", "null"}:
        return None
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return s if keep_commas else s.replace(",", "")


def split_name(fullname: str | None):
    if not fullname or not isinstance(fullname, str):
        return None, None

    fullname = fullname.strip()

    # Always "Last, First"
    parts = [p.strip() for p in fullname.split(",", 1)]
    last = parts[0]
    first = parts[1] if len(parts) > 1 else ""
    return last, first
    
def first_code_only(val: Any) -> str | None:
    """Return only the first ICD code from a comma-separated list."""
    s = to_str_or_none(val, keep_commas=True)
    if not s:
        return None
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts[0] if parts else None





# ------------------ MAPPING ASSUMED ------------------ #
mapping_assumed = {
    "NOTE ID": "note_id",
    "PRACTICE": "Anchor Home Healthcare",
    "ACCT": "Paradigm Rehab",
    "PATIENT ID": "patient_id",
    "PATIENT LASTNAME": "last_name",
    "PATIENT FIRSTNAME": "first_name",
    "PATIENT ADDRESS 1": "lookup:patients.address",
    "PATIENT ADDRESS 2": "lookup:patients.address2",
    "PATIENT CITY": "lookup:patients.city",
    "PATIENT STATE": "lookup:patients.state",
    "PATIENT ZIP CODE": "lookup:patients.zip",
    "PATIENT BIRTH": "date_of_birth",
    "PATIENT GENDER": "gender",
    "PATIENT SSN": "999-99-9999",
    "FINANCIAL CLASS": "",
    "LASTNAME REFERRING PHYS": "referring_provider",
    "FIRSTNAME REFERRING PHYS": "referring_provider",
    "REFERRING PHYS NPI": "ref_provider_npi",
    "PRIMARY INS NAME": "primary_insurance",
    "PRIMARY INS POLICY ID": "primary_ins_id",
    "SECONDARY INS NAME": "secondary_insurance",
    "SECONDARY INS POLICY": "secondary_ins_id",
    "TERTIARY INS NAME": "",
    "TERTIARY INS POLICY": "",
    "DATE OF SERVICE": "note_date",
    "MODIFIER SPECIALTY": "modifier_specialty",
    "59 MODIFIER": "modifier_59",
    "ASSISTANT MODIFIER": "",     # not parsed in your examples
    "CPT CODE": "cpt_code",
    "UNITS": "total_units",
    "MEDICAL DX1": "medical_diagnosis",
    "MEDICAL DX2": "medical_diagnosis",
    "Treatment DX 1": "diagnosis",
    "Treatment DX 2": "diagnosis",
    "PROVIDER LASTNAME": "visiting_therapist",
    "PROVIDER FIRSTNAME": "visiting_therapist",
    "SUPERVISOR LASTNAME": "supervising_therapist",
    "SUPERVISOR FIRSTNAME": "supervising_therapist",
    "KX MODIFIER": "modifier_kx",
    "TELEHEALTH MODIFIER": "",    # not parsed in your examples
    "FACILITY NAME": "location",
    "PLACE OF SERVICE": "pos",
    "AUTHORIZATION REFERENCE NUMBER": "auth_number",
}



## ------------------ HELPERS ------------------ #
def nth_code(val: str | None, n: int) -> str | None:
    """Return the nth ICD code (1-based) from a comma-separated string."""
    if not val or not isinstance(val, str):
        return None
    parts = [p.strip() for p in val.split(",") if p.strip()]
    return parts[n-1] if len(parts) >= n else None


# ------------------ ROUTE ------------------ #
@router.get("/billable-notes")
async def download_billable_notes(
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Excel with billable notes filtered by service date.
    Includes logic to extract only the first/second ICD codes
    for MEDICAL DX1/2 and Treatment DX 1/2.
    """
    stmt = (
        select(Visit, Patient)
        .join(Patient, Patient.id == Visit.patient_id)
    )
    if start_date:
        stmt = stmt.where(Visit.note_date >= start_date)
    if end_date:
        stmt = stmt.where(Visit.note_date <= end_date)

    # Get visits + patient info
    result = await db.execute(stmt)
    rows = result.all()

    billable_rows = []
    for visit, patient in rows:
        parsed_cpts = parse_cpt_string(visit.cpt_code)

        for cpt in parsed_cpts:
            record = {}
            for excel_col, mapping in mapping_assumed.items():
                if mapping is None:
                    record[excel_col] = None
                elif mapping == "":
                    record[excel_col] = ""
                elif mapping.startswith("lookup:patients."):
                    field = mapping.split(".")[1]
                    record[excel_col] = getattr(patient, field, None)

                # --- special handling for provider name splits --- #
                elif mapping in {"referring_provider", "visiting_therapist", "supervising_therapist"}:
                    full = getattr(visit, mapping, None)
                    last, first = split_name(full)
                    if "LASTNAME" in excel_col:
                        record[excel_col] = last
                    elif "FIRSTNAME" in excel_col:
                        record[excel_col] = first
                    else:
                        record[excel_col] = full

                # --- special handling for DX fields --- #
                elif excel_col == "MEDICAL DX1":
                    record[excel_col] = nth_code(getattr(visit, "medical_diagnosis", None), 1)
                elif excel_col == "MEDICAL DX2":
                    record[excel_col] = nth_code(getattr(visit, "medical_diagnosis", None), 2)
                elif excel_col == "Treatment DX 1":
                    record[excel_col] = nth_code(getattr(visit, "diagnosis", None), 1)
                elif excel_col == "Treatment DX 2":
                    record[excel_col] = nth_code(getattr(visit, "diagnosis", None), 2)


                # --- CPT values from parsed_cpts --- #
                elif mapping in cpt:
                    record[excel_col] = cpt[mapping]

                # --- default: attribute from visit --- #
                elif hasattr(visit, mapping):
                    record[excel_col] = getattr(visit, mapping, None)

                else:
                    record[excel_col] = mapping

            billable_rows.append(record)

    # Convert to DataFrame
    df = pd.DataFrame(billable_rows)

    # Export to Excel in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="BillableNotes")
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=billable_notes.xlsx"}
    )
