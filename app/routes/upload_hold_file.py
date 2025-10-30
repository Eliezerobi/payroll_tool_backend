from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, update
from pathlib import Path
from io import BytesIO
import pandas as pd

from app.database import get_db
from app.models.users import User
from app.models.visits import Visit
from app.dependencies.auth import get_current_user
from app.routes.upload_visit_file import (
    ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB,
    normalize_and_map_columns, clean_dataframe_for_db,
    split_therapists, clean_supervising_column
)

router = APIRouter()   # 👈 this is what was missing

def get_review_by():
    """Placeholder function for review_by."""
    
    return 3


@router.post("/upload-hold-report")
async def upload_hold_report(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Only .xlsx, .xls, .csv allowed")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large ({size_mb:.1f} MB). Max {MAX_FILE_SIZE_MB} MB allowed")

    try:
        df = pd.read_csv(BytesIO(contents)) if ext == ".csv" else pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {str(e)}")

    # Normalize + clean
    df = normalize_and_map_columns(df)
    if "date_billed" in df.columns:
        df = df.drop(columns=["date_billed"])
    df = clean_dataframe_for_db(df)
    df = split_therapists(df)
    df = clean_supervising_column(df)

    # ✅ Only rows with hold = true
    if "hold" in df.columns:
        df = df[df["hold"] == True]

    rows = df.to_dict(orient="records")

    updated = 0
    inserted = 0

    for row in rows:
        note_id = row.get("note_id")
        if not note_id:
            continue

        # Check if note_id exists
        result = await db.execute(select(Visit).where(Visit.note_id == note_id))
        visit = result.scalar_one_or_none()

        if visit:
            # If exists → update review fields
            review_reason = "post_payroll" if row.get("paid") else "pre_payroll"
            q = (
                update(Visit)
                .where(Visit.note_id == note_id)
                .values(
                    review_needed=True,
                    review_by=get_review_by(),
                    review_reason=review_reason,
                )
            )
            await db.execute(q)
            updated += 1
        else:
            # If not exists → insert the row as new
            row["uploaded_by"] = current_user.id
            stmt = insert(Visit).values(row)
            await db.execute(stmt)
            inserted += 1

    await db.commit()

    return {
        "message": f"✅ Processed {len(rows)} hold rows",
        "updated": updated,
        "inserted": inserted,
    }