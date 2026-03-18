from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.biling_import import parse_billed_excel, import_billed_notes_from_rows

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.post("/import-billed-excel")
async def import_billed_excel(
    file: UploadFile = File(...),
    skip_if_already_billed: bool = True,
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Please upload an Excel file (.xlsx or .xls).")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file.")

    try:
        rows, duplicates = parse_billed_excel(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read Excel: {e}")

    if not rows:
        raise HTTPException(status_code=400, detail="No valid note_id rows found in the Excel file.")

    try:
        result = await import_billed_notes_from_rows(
            db, rows, skip_if_already_billed=skip_if_already_billed
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {
        "ok": True,
        "processed": result.processed,
        "created_billing_status": result.created_billing_status,
        "updated_visits": result.updated_visits,
        "missing_note_ids": result.missing_note_ids,
        "duplicate_note_ids": duplicates,
        "already_billed_note_ids": result.already_billed_note_ids,
        "skip_if_already_billed": skip_if_already_billed,
    }
