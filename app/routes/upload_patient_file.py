from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from pathlib import Path
from io import BytesIO
import pandas as pd
import numpy as np
import re
from typing import Any

from app.database import get_db
from app.models.users import User
from app.models.patients import Patient
from app.dependencies.auth import get_current_user

router = APIRouter()

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
MAX_FILE_SIZE_MB = 10
BATCH_SIZE = 500  # keep < 32767 bind params (asyncpg limit)


# ---------- Helpers ----------
def _normalize(col: str) -> str:
    """Normalize header names: lowercase, underscores, strip non-alnum."""
    return re.sub(r"[^a-z0-9]+", "_", col.strip().lower()).strip("_")


HEADER_ALIASES = {
    "patient_id": "id",
    "first_name": "first_name",
    "last_name": "last_name",
    "dob": "date_of_birth",
    "gender": "gender",
    "address": "address",
    "city": "city",
    "state": "state",
    "zip": "zip",
    "phone": "phone",
    "work_phone": "work_phone",
    "mobile_phone": "mobile_phone",
    "primary_insurance": "primary_insurance",
    "primary_plan_name": "primary_plan_name",
    "primary_insurance_id": "primary_ins_id",
    "secondary_insurance": "secondary_insurance",
    "secondary_plan_name": "secondary_plan_name",
    "secondary_insurance_id": "secondary_ins_id",
    "m_r_number": "medical_record_no",
    "email": "email",
    "status": "status",
    "comment": "comment",
    "primary_care_physician": "primary_care_physician",
    "date_added": "date_added",
}


def normalize_and_map_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    normalized = [_normalize(c) for c in df.columns]
    df.columns = normalized
    rename_map = {c: HEADER_ALIASES.get(c, c) for c in normalized}
    return df.rename(columns=rename_map)


def to_str_or_none(x: Any) -> str | None:
    if x is None:
        return None
    if isinstance(x, float) and np.isnan(x):
        return None
    s = str(x).strip()
    if s.lower() in {"", "nan", "nat", "none", "null"}:
        return None
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return s


def clean_dataframe_for_db(df: pd.DataFrame) -> pd.DataFrame:
    df = df.where(pd.notna(df), None)

    # Dates
    if "date_of_birth" in df.columns:
        df["date_of_birth"] = pd.to_datetime(df["date_of_birth"], errors="coerce").dt.date
        df["date_of_birth"] = df["date_of_birth"].where(pd.notna(df["date_of_birth"]), None)

    if "date_added" in df.columns:
        df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce").dt.date
        df["date_added"] = df["date_added"].where(pd.notna(df["date_added"]), None)

    # Strings
    varchar_cols = [
        "first_name", "last_name", "gender", "address", "city", "state", "zip",
        "phone", "work_phone", "mobile_phone",
        "primary_insurance", "primary_plan_name", "primary_ins_id",
        "secondary_insurance", "secondary_plan_name", "secondary_ins_id",
        "medical_record_no", "email", "status", "comment", "primary_care_physician"
    ]
    for c in varchar_cols:
        if c in df.columns:
            df[c] = df[c].map(to_str_or_none)

    # Integers
    if "id" in df.columns:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
        df["id"] = df["id"].map(lambda v: int(v) if pd.notna(v) else None)

    return df


def chunked(seq: list[dict[str, Any]], size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def build_upsert_stmt(rows_batch: list[dict[str, Any]]):
    """
    Build INSERT ... ON CONFLICT (id) DO UPDATE for a single batch.
    Updates all columns except id/created_at; updates updated_at if present.
    """
    stmt = insert(Patient).values(rows_batch)
    excluded = stmt.excluded

    update_cols: dict[str, Any] = {}
    for col in Patient.__table__.columns:
        if col.name in {"id", "created_at"}:
            continue
        update_cols[col.name] = getattr(excluded, col.name)

    colnames = {c.name for c in Patient.__table__.columns}
    if "updated_at" in colnames:
        update_cols["updated_at"] = func.now()

    return stmt.on_conflict_do_update(
        index_elements=[Patient.id],
        set_=update_cols
    )


# ---------- Route ----------
@router.post("/patients/upload")
async def upload_patients_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload and process a patients file (CSV/XLSX).
    - Validates file
    - Parses to DataFrame
    - Normalizes/cleans columns
    - UPSERTS into patients (insert new, update existing) in batches
    """

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {ext}. Only {', '.join(sorted(ALLOWED_EXTENSIONS))} allowed."
        )

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size_mb:.1f} MB). Max {MAX_FILE_SIZE_MB} MB allowed."
        )

    # Parse into DataFrame
    try:
        if ext == ".csv":
            df = pd.read_csv(BytesIO(contents))
        else:
            df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    # Normalize + map headers
    df = normalize_and_map_columns(df)

    # Required columns
    required_cols = {"id", "first_name", "last_name", "date_of_birth"}
    missing = required_cols - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(sorted(missing))}"
        )

    # Clean for DB
    df = clean_dataframe_for_db(df)
    rows = df.to_dict(orient="records")

    # Only keep valid model columns, and drop rows with no id
    valid_fields = {c.name for c in Patient.__table__.columns}
    cleaned_rows = [
        {k: v for k, v in row.items() if k in valid_fields}
        for row in rows
        if row.get("id") is not None
    ]

    if not cleaned_rows:
        raise HTTPException(status_code=400, detail="No valid rows found (all missing patient id).")

    try:
        for batch in chunked(cleaned_rows, BATCH_SIZE):
            stmt = build_upsert_stmt(batch)
            await db.execute(stmt)

        await db.commit()

    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected database error: {e}")

    return {"message": f"✅ Uploaded {len(cleaned_rows)} patients successfully"}
