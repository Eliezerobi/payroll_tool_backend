from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.crud.patients.deductibleFile import import_met_deductible_from_excel_bytes

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("/import-deductible-flags")
async def import_deductible_flags(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # ---- validate file type ----
    filename = (file.filename or "").lower()
    if not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls).",
        )

    # ---- read file ----
    try:
        excel_bytes = await file.read()
        if not excel_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read upload: {str(e)}")

    # ---- run import ----
    try:
        # ✅ MUST await — this was missing
        result = await import_met_deductible_from_excel_bytes(db, excel_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    return {
        "filename": file.filename,
        **result,
    }
