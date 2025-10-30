from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func
from pathlib import Path
from io import BytesIO
import pandas as pd
import numpy as np
import re
from typing import Any
from datetime import date

from app.database import get_db
from app.models.users import User
from app.models.visits import Visit
from app.dependencies.auth import get_current_user
from app.crud.visits import insert_visit_rows

router = APIRouter()

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
MAX_FILE_SIZE_MB = 10


# ---------- Helpers ----------
def _normalize(col: str) -> str:
    """Normalize header names: lowercase, underscores, strip non-alnum."""
    return re.sub(r"[^a-z0-9]+", "_", col.strip().lower()).strip("_")


HEADER_ALIASES = {
    # required
    "note_id": "note_id",
    "patient_id": "patient_id",
    "first_name": "first_name",
    "last_name": "last_name",
    "case_description": "case_description",
    "date_of_birth": "date_of_birth",

    # therapist
    "therapist": "visiting_therapist",  # Excel "Therapist" → DB visiting_therapist
    "supervising_therapist": "supervising_therapist",

    # insurance
    "primary": "primary_insurance",
    "primary_ins_id": "primary_ins_id",
    "primary_insurance": "primary_insurance",
    "2ndry_ins_id": "secondary_ins_id",
    "2ndry_insurance": "secondary_insurance",
    "secondary_ins_id": "secondary_ins_id",
    "secondary_insurance": "secondary_insurance",

    # dates and misc
    "note": "note",
    "case_date": "case_date",
    "note_date": "note_date",
    "referring_provider": "referring_provider",
    "ref_provider_npi": "ref_provider_npi",
    "diagnosis": "diagnosis",
    "finalized_date": "finalized_date",
    "pos": "pos",
    "visit_type": "visit_type",
    "attendance": "attendance",
    "comments": "comments",
    "cpt_code": "cpt_code",
    "cpt_code_g_code": "cpt_code",
    "total_units": "total_units",
    "date_billed": "date_billed",
    "date_billed_last_reviewed": "date_billed",
    "billed_comment": "billed_comment",
    "address": "address",
    "case_type": "case_type",
    "location": "location",
    "hold": "hold",
    "billed": "billed",
    "paid": "paid",
    "auth": "auth_number",
    "auth_number": "auth_number",
    "medical_record_no": "medical_record_no",
    "medical_diagnosis": "medical_diagnosis",
    "rendering_provider_npi": "rendering_provider_npi",
    "gender": "gender",
}



def normalize_and_map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize headers and map them to DB model fields."""
    df = df.copy()
    normalized = [_normalize(c) for c in df.columns]
    df.columns = normalized
    rename_map = {c: HEADER_ALIASES.get(c, c) for c in normalized}
    return df.rename(columns=rename_map)


def to_str_or_none(x: Any, keep_commas: bool = False) -> str | None:
    """Convert values to string or None. Optionally keep commas (for diagnosis fields)."""
    if x is None:
        return None
    if isinstance(x, float) and np.isnan(x):
        return None
    s = str(x).strip()
    if s.lower() in {"", "nan", "nat", "none", "null"}:
        return None
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return s if keep_commas else s.replace(",", "")


def clean_therapist_name(name: str | None) -> str | None:
    """Remove known suffixes/titles from therapist names and trim."""
    if not name or not isinstance(name, str):
        return None

    # Titles/suffixes to strip
    suffixes = [
        "PT", "OT","M.S., CCC-SLP" ,"SLP",
        "Occupational Therapist",
        "M.S., CCC-SLP",
        "PTA", "OTA",
        "Speech Language Pathologist",
        "PTA, ATC, CAFS", "Doctor of Physical Therapy" ,"OTR/L"
    ]

    cleaned = name
    for suffix in suffixes:
        # remove if suffix appears at the end (case-insensitive, optional punctuation/spaces)
        cleaned = re.sub(rf"\s*,?\s*{re.escape(suffix)}\s*$", "", cleaned, flags=re.IGNORECASE)

    return cleaned.strip() or None


def to_bool(x: Any) -> bool | None:
    """Convert to bool if possible."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip().lower()
    if s in {"true", "1", "yes", "y"}:
        return True
    if s in {"false", "0", "no", "n"}:
        return False
    return None

import re



def clean_dataframe_for_db(df: pd.DataFrame) -> pd.DataFrame:
    df = df.where(pd.notna(df), None)

    # Dates
    for col in ["note_date", "case_date", "finalized_date", "date_of_birth", "date_billed"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
            df[col] = df[col].where(pd.notna(df[col]), None)

    # Extract note_number
    if "note" in df.columns:
        def extract_note_number(note: Any) -> int | None:
            if not note or not isinstance(note, str):
                return None
            match = re.search(r"-\s*(\d+)\s*$", note)
            if match:
                return int(match.group(1))
            return None
        df["note_number"] = df["note"].map(extract_note_number)

    # Strings — default (commas removed)
    varchar_cols = [
        "first_name", "last_name", "note", "case_description",
        "primary_ins_id", "primary_insurance",
        "secondary_ins_id", "secondary_insurance",
        "referring_provider", "ref_provider_npi",
        "pos", "visit_type", "attendance",
        "comments", "cpt_code", "billed_comment",
        "address", "case_type", "location",
        "auth_number", "medical_record_no",
        "rendering_provider_npi", "gender"
    ]
    for c in varchar_cols:
        if c in df.columns:
            df[c] = df[c].map(lambda v: to_str_or_none(v, keep_commas=False))

    # Strings — special case (keep commas)
    for c in ["diagnosis", "medical_diagnosis"]:
        if c in df.columns:
            df[c] = df[c].map(lambda v: to_str_or_none(v, keep_commas=True))

    # Integers
    for c in ["total_units", "note_id", "patient_id"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
            df[c] = df[c].map(lambda v: int(v) if pd.notna(v) else None)

    # Booleans
    for c in ["hold", "billed", "paid"]:
        if c in df.columns:
            df[c] = df[c].map(to_bool)

    return df


def split_therapists(df: pd.DataFrame) -> pd.DataFrame:
    if "visiting_therapist" in df.columns:
        visiting = []
        supervising = []
        for val in df["visiting_therapist"]:
            if not val or not isinstance(val, str):
                visiting.append(None)
                supervising.append(None)
                continue

            match = re.match(r"^(.*)\((?:cosigned by\s*)?(.*)\)$", val.strip())
            if match:
                # before parentheses
                main = match.group(1).strip(" ,")
                # inside parentheses
                sup = match.group(2).strip()
                visiting.append(main if main else None)
                supervising.append(sup if sup else None)
            else:
                visiting.append(val.strip())
                supervising.append(None)

        df["visiting_therapist"] = visiting
        # ensure column exists
        df["supervising_therapist"] = supervising
    return df

def clean_supervising_column(df: pd.DataFrame) -> pd.DataFrame:
    if "supervising_therapist" in df.columns:
        df["supervising_therapist"] = df["supervising_therapist"].map(
            lambda x: None if isinstance(x, str) and "cavero" in x.lower() else x
        )
    return df



# ---------- Route ----------
@router.post("/upload-visit-file")
async def upload_visit_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload and process a visits file (CSV/XLSX).
    Steps:
      1. Validate file type and size
      2. Parse into DataFrame
      3. Normalize + clean columns
      4. Add visit_uid (re-use if conflict, create if new)
      5. Insert into DB
    """

    # --- Gate 1: file type ---
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {ext}. Only {', '.join(ALLOWED_EXTENSIONS)} allowed."
        )

    # --- Gate 2: file size ---
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size_mb:.1f} MB). Max {MAX_FILE_SIZE_MB} MB allowed."
        )

    # --- Gate 3: parse file into DataFrame ---
    try:
        if ext == ".csv":
            df = pd.read_csv(BytesIO(contents))
        else:
            df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    # --- Normalize + drop unused columns ---
    df = normalize_and_map_columns(df)
    df = df.drop(columns=[c for c in ["date_billed", "cptcode_details"] if c in df.columns])

    # --- Gate 4: check required columns ---
    required_cols = {
        "note_id",
        "patient_id",
        "first_name",
        "last_name",
        "case_description",
        "date_of_birth",
        "visiting_therapist",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(sorted(missing))}"
        )

    # --- Clean + prep DataFrame for DB ---
    df = clean_dataframe_for_db(df)
    df = split_therapists(df)
    df = clean_supervising_column(df)
    
    if "visiting_therapist" in df.columns:
        df["visiting_therapist"] = df["visiting_therapist"].map(clean_therapist_name)

    if "supervising_therapist" in df.columns:
        df["supervising_therapist"] = df["supervising_therapist"].map(clean_therapist_name)


    rows = df.to_dict(orient="records")
    # --- Step 6: insert into DB ---
    try:
        result = await insert_visit_rows(db, rows, uploaded_by=current_user.id)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate note_id found — already in DB.")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected database error: {e}")

    # --- Response ---
    return {
        "message": f"✅ Uploaded {result['inserted_count']} visit rows successfully",
        "skipped": result["skipped_notes"],
        "visit_uids_created": result["visit_uids_created"],
    }
