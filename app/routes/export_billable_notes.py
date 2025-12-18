import re
import json
from collections import defaultdict
from io import BytesIO
from datetime import date
from typing import Any
from sqlalchemy import or_, text

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.visits import Visit
from app.models.patients import Patient
from app.dependencies.auth import get_current_user
from app.models.users import User

router = APIRouter()

# ------------------ TITLES TO REMOVE ------------------ #
titles_to_remove = [
    "CF-SLP","M.S., CCC-SLP", "PTA", "OTA", "CFY",  "DPT", "CCC-SLP",
    "PTA ATC CAFS", "Speech Language Pathologist", "CFY/SLP", "OTR/L",
    "Occupational Therapist", "Doctor of Physical Therapy",
    "PTA, ATC, CAFS", "Slps", 
    "Physical Therapist Assistant",
    "Cavero Michelle Ph.D. CCC-SLP TSSLD",
    "Nicole CLINICAL DIRECTOR OF SPEECH-LANGUAGE PATHOLOGY Yehezel","PT", "OT", "SLP"
]

#------------------ MEDICARE PRIMARY NAMES ------------------ #
MEDICARE_PRIMARY_NAMES = {
    "new york empire medicare",
    "new york medicare ghi",
    "new york medicare upstate"
}


# ------------------ NAME HELPERS ------------------ #
def _strip_titles(name: str | None) -> str | None:
    if not name or not isinstance(name, str):
        return None
    cleaned = name
    for t in titles_to_remove:
        cleaned = re.sub(rf"\b{re.escape(t)}\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(",")
    return cleaned or None


def split_provider_and_supervisor(raw: str | None) -> tuple[str | None, str | None]:
    """
    primary = visiting therapist (outside parentheses)
    supervisor = name inside parentheses

    Examples:
      'Prieto, Napoleon PTA (cosigned by Cruz, Van Gabriel PT)'
        -> ('Prieto, Napoleon', 'Cruz, Van Gabriel')

      'John Doe PT (Jane Smith DPT)'
        -> ('John Doe', 'Jane Smith')
    """
    if not raw or not isinstance(raw, str):
        return None, None

    raw = raw.strip()

    # Supervisor: inside parentheses
    m = re.search(r"\((.*?)\)", raw)
    supervisor_raw = m.group(1).strip() if m else None

    if supervisor_raw:
        # Remove "cosigned by"/"co-signed by" prefix if present
        supervisor_raw = re.sub(
            r"(?i)^\s*co-?signed by\s+",
            "",
            supervisor_raw
        ).strip()

    # Provider: remove parentheses section
    provider_raw = re.sub(r"\(.*?\)", "", raw).strip()

    provider = _strip_titles(provider_raw)
    supervisor = _strip_titles(supervisor_raw) if supervisor_raw else None

    return provider, supervisor


# ------------------ NAME SPLITTER ------------------ #
def split_first_last(name: str | None) -> tuple[str | None, str | None]:
    """
    Handles both:
      'Prieto, Napoleon' -> ('Napoleon', 'Prieto')
      'John Doe'         -> ('John', 'Doe')
      'John'             -> ('John', None)
    """
    if not name or not isinstance(name, str):
        return None, None

    name = name.strip()

    # Format: "Last, First ..."
    if "," in name:
        last_part, first_part = [p.strip() for p in name.split(",", 1)]
        first_name = first_part if first_part else None
        last_name = last_part if last_part else None
        return first_name or None, last_name or None

    # Format: "First Last ..."
    parts = name.split()
    if len(parts) == 1:
        return parts[0], None
    first_name = parts[0]
    last_name = " ".join(parts[1:]) if len(parts) > 1 else None
    return first_name, last_name


# ------------------ CPT PARSER ------------------ #
def parse_cpt_string(cpt_str: str):
    if not cpt_str or not isinstance(cpt_str, str):
        return []

    parts = cpt_str.split(":")
    modifiers = []
    discipline = None

    if parts[0] in {"GP", "GO", "GN"}:
        discipline = parts[0]
        modifiers = parts[1:]
    else:
        modifiers = parts

    cpt_part = ""
    for i, m in enumerate(modifiers):
        if re.search(r"\d{5}\(\d+\)", m):
            cpt_part = ":".join(modifiers[i:])
            modifiers = modifiers[:i]
            break

    # Flags (presence in modifiers list)
    has_59 = "59" in modifiers
    has_kx = "KX" in modifiers
    has_cq = "CQ" in modifiers
    has_co = "CO" in modifiers

    # Assistant modifier should be a single value: CQ or CO (never both)
    assistant_modifier = None
    if has_cq and not has_co:
        assistant_modifier = "CQ"
    elif has_co and not has_cq:
        assistant_modifier = "CO"
    # if both present, leave None so it can be reviewed/handled elsewhere

    cpt_matches = re.findall(r"(\d{5})\((\d+)\)", cpt_part)
    cpt_units = defaultdict(int)
    for code, units in cpt_matches:
        cpt_units[code] += int(units)

    rows = []
    for code, units in cpt_units.items():
        rows.append({
            "cpt_code": code,
            "total_units": units,
            "modifier_specialty": discipline,
            "modifier_59": "59" if has_59 else None,
            "modifier_kx": "KX" if has_kx else None,
            "assistant_modifier": assistant_modifier,
        })

    return rows



# ------------------ HELPERS ------------------ #
def nth_code(val: str | None, n: int) -> str | None:
    if not val or not isinstance(val, str):
        return None
    parts = [p.strip() for p in val.split(",") if p.strip()]
    return parts[n-1] if len(parts) >= n else None


def split_referring_phys(name: str | None) -> tuple[str | None, str | None]:
    if not name or not isinstance(name, str):
        return None, None

    name = name.strip()

    # Rule 1: Double space splits first/last
    if "  " in name:
        first, last = name.split("  ", 1)
        return first.strip(), last.strip()

    # Rule 2: Otherwise first word = first name, rest = last name
    parts = name.split()

    if len(parts) == 1:
        return parts[0], None

    first_name = parts[0]
    last_name = " ".join(parts[1:])

    return first_name, last_name


# ------------------ COLUMN MAPPING ------------------ #
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

    "PRIMARY INS NAME": "primary_insurance",
    "PRIMARY INS POLICY ID": "primary_ins_id",
    "SECONDARY INS NAME": "secondary_insurance",
    "SECONDARY INS POLICY": "secondary_ins_id",
    "TERTIARY INS NAME": "",
    "TERTIARY INS POLICY": "",

    "DATE OF SERVICE": "note_date",

    "MODIFIER SPECIALTY": "modifier_specialty",
    "59 MODIFIER": "modifier_59",
    "KX MODIFIER": "modifier_kx",
    "ASSISTANT MODIFIER": "assistant_modifier",
    "TELEHEALTH MODIFIER": "",
    "CPT CODE": "cpt_code",
    "UNITS": "total_units",

    "MEDICAL DX1": "medical_diagnosis",
    "MEDICAL DX2": "medical_diagnosis",
    "Treatment DX 1": "diagnosis",
    "Treatment DX 2": "diagnosis",

    # Provider / Supervisor: both sourced from visiting_therapist,
    # we split them in code.

    "PROVIDER FIRSTNAME": "visiting_therapist",
    "PROVIDER LASTNAME": "visiting_therapist",

    "SUPERVISOR FIRSTNAME": "visiting_therapist",
    "SUPERVISOR LASTNAME": "visiting_therapist",

    "FACILITY NAME": "location",
    "PLACE OF SERVICE": "pos",
    "AUTHORIZATION REFERENCE NUMBER": "auth_number",

    "FIRSTNAME REFERRING PHYS": "referring_provider",
    "LASTNAME REFERRING PHYS": "referring_provider",

    "REFERRING PHYS NPI": "ref_provider_npi",
}


# ------------------ ROUTE ------------------ #
@router.get("/billable-notes")
async def download_billable_notes(
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    stmt = (
        select(Visit, Patient)
        .join(Patient, Patient.id == Visit.patient_id)
    )

    if start_date:
        stmt = stmt.where(Visit.note_date >= start_date)
    if end_date:
        stmt = stmt.where(Visit.note_date <= end_date)

    # Exclude HOLD: keep False / NULL, drop True
    stmt = stmt.where(Visit.hold.isnot(True))

    # Exclude certain insurance
    stmt = stmt.where(
        ~or_(
            Visit.primary_insurance.ilike("americare"),
            Visit.primary_insurance.ilike("royal care"),
            Visit.primary_insurance.ilike("extendedcare"),
            Visit.primary_insurance.ilike("able health"),
        )
    )

    result = await db.execute(stmt)
    rows = result.all()

    # ---------- LOAD COVERAGE MAP (patient_coverages_flat) ---------- #
    # We match by medical_record_no -> medical_record_id
    coverage_result = await db.execute(text("""
        SELECT
            medical_record_id,
            medicare_payer,
            medicare_policy_type,
            medicare_policy_number,
            medicaid_payer,
            medicaid_policy_type,
            medicaid_policy_number
        FROM patient_coverages_flat
    """))
    coverage_rows = coverage_result.mappings().all()

    coverage_by_medrec = {
        row["medical_record_id"]: row for row in coverage_rows
    }

    billable_rows = []

    for visit, patient in rows:
        parsed_cpts = parse_cpt_string(visit.cpt_code)

        # Find coverage row by patient_id -> medical_record_id
        coverage = None
        if visit.patient_id is not None:
            coverage = coverage_by_medrec.get(str(visit.patient_id))

        for cpt in parsed_cpts:
                    # ---------- RULE: If there is a supervisor, force assistant modifier based on specialty ----------
            _provider_full, _supervisor_full = split_provider_and_supervisor(getattr(visit, "visiting_therapist", None))

            if _supervisor_full:
                specialty = (cpt.get("modifier_specialty") or "").strip().upper()

                # GO (OT) => CO
                if specialty == "GO":
                    cpt["assistant_modifier"] = "CO"

                # GP (PT) => CQ
                elif specialty == "GP":
                    cpt["assistant_modifier"] = "CQ"




            record = {}

            for excel_col, mapping in mapping_assumed.items():

                # ----- Patient lookups ----- #
                if isinstance(mapping, str) and mapping.startswith("lookup:patients."):
                    field = mapping.split(".")[1]
                    record[excel_col] = getattr(patient, field, None)

                # ----- Provider / Supervisor (all variants) ----- #
                elif mapping == "visiting_therapist" and (
                    excel_col.startswith("PROVIDER") or excel_col.startswith("SUPERVISOR")
                ):
                    raw = getattr(visit, "visiting_therapist")
                    provider_full, supervisor_full = split_provider_and_supervisor(raw)

                    prov_first, prov_last = split_first_last(provider_full)
                    sup_first, sup_last = split_first_last(supervisor_full)

                    if excel_col == "PROVIDER FIRSTNAME":
                        record[excel_col] = prov_first
                    elif excel_col == "PROVIDER LASTNAME":
                        record[excel_col] = prov_last
                    elif excel_col == "SUPERVISOR FIRSTNAME":
                        record[excel_col] = sup_first
                    elif excel_col == "SUPERVISOR LASTNAME":
                        record[excel_col] = sup_last

                # ----- Diagnosis mapping ----- #
                elif excel_col == "MEDICAL DX1":
                    record[excel_col] = nth_code(visit.medical_diagnosis, 1)

                elif excel_col == "MEDICAL DX2":
                    record[excel_col] = nth_code(visit.medical_diagnosis, 2)

                elif excel_col == "Treatment DX 1":
                    record[excel_col] = nth_code(visit.diagnosis, 1)

                elif excel_col == "Treatment DX 2":
                    record[excel_col] = nth_code(visit.diagnosis, 2)

                # ----- Referring provider fields (trim name) ----- #
                elif mapping == "referring_provider":
                    raw = getattr(visit, "referring_provider")
                    raw = raw.strip() if isinstance(raw, str) else raw

                    ref_first, ref_last = split_referring_phys(raw)

                    if excel_col == "FIRSTNAME REFERRING PHYS":
                        record[excel_col] = ref_first
                    elif excel_col == "LASTNAME REFERRING PHYS":
                        record[excel_col] = ref_last
                    else:
                        record[excel_col] = None

                # ----- CPT row fields ----- #
                elif isinstance(mapping, str) and mapping in cpt:
                    record[excel_col] = cpt[mapping]

                # ----- Direct visit attributes ----- #
                elif isinstance(mapping, str) and hasattr(visit, mapping):
                    value = getattr(visit, mapping)

                    # Rule: if auth number is "x" or "eval", set to None
                    if excel_col == "AUTHORIZATION REFERENCE NUMBER":
                        if isinstance(value, str) and value.strip().lower() in {"x", "eval"}:
                            value = None

                    record[excel_col] = value

                # ----- Static / default mapping values ----- #
                else:
                    record[excel_col] = mapping

            # ---------- Correct Primary / Secondary Payer ---------- #
            correct_primary = None
            correct_secondary = None

            # 1️⃣ Base logic from patient_coverages_flat
            if coverage:
                med_payer = (coverage.get("medicare_payer") or "").strip()
                med_type = (coverage.get("medicare_policy_type") or "").strip()
                medicaid_payer = (coverage.get("medicaid_payer") or "").strip()
                medicaid_type = (coverage.get("medicaid_policy_type") or "").strip()

                # Primary (from Medicare fields)
                if med_payer and med_payer.lower() != "medicare":
                    correct_primary = f"{med_payer} | {med_type}" if med_type else med_payer

                # Secondary (from Medicaid fields)
                if medicaid_payer and medicaid_payer.lower() != "medicaid":
                    correct_secondary = f"{medicaid_payer} | {medicaid_type}" if medicaid_type else medicaid_payer


            # 2️⃣ OVERRIDE: Specific Medicare plan names on the VISIT always win
            primary_ins = (getattr(visit, "primary_insurance", None) or "").strip()

            if primary_ins and primary_ins.lower() in {
                "new york empire medicare",
                "new york medicare ghi",
                "new york medicare upstate"
            }:
                correct_primary = f"{primary_ins} | Medicare"


            record["Correct Primary Payer"] = correct_primary
            record["Correct Secondary Payer"] = correct_secondary

            billable_rows.append(record)

    df = pd.DataFrame(billable_rows)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="BillableNotes")
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=billable_notes.xlsx"}
    )
