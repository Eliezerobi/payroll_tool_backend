from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.users import User
from app.models.visits import Visit  # <-- adjust to your actual model import
from app.schemas.visits import VisitBulkUpdateIn, VisitDetailsOut, VisitDetailsUpdate

router = APIRouter(prefix="/visits", tags=["Visits"])

ALLOWED_UPDATE_FIELDS = {
    "primary_insurance",
    "secondary_insurance",
    "primary_ins_id",
    "secondary_ins_id",
    "ref_provider_npi",
    "referring_provider",
    "diagnosis",
    "visiting_therapist",
    "cpt_code",
    "auth_number",
    "medical_diagnosis",
    "rendering_provider_npi",
}


@router.get("/note-details", response_model=VisitDetailsOut)
async def get_note_details(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Fetch full visit/note details by note_id.

    This is intended for the right-side drawer in BillingDayView.
    """
    stmt = select(Visit).where(Visit.note_id == note_id)
    res = await db.execute(stmt)
    visit = res.scalar_one_or_none()

    if not visit: 
        raise HTTPException(status_code=404, detail=f"Visit with note_id={note_id} not found")

    return visit


@router.get("/insurance-options")
async def get_insurance_options(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Return unique insurance values for searchable dropdowns.
    """
    primary_stmt = (
        select(Visit.primary_insurance)
        .where(Visit.primary_insurance.is_not(None), Visit.primary_insurance != "")
        .distinct()
        .order_by(Visit.primary_insurance.asc())
    )
    secondary_stmt = (
        select(Visit.secondary_insurance)
        .where(Visit.secondary_insurance.is_not(None), Visit.secondary_insurance != "")
        .distinct()
        .order_by(Visit.secondary_insurance.asc())
    )

    primary_rows = (await db.execute(primary_stmt)).scalars().all()
    secondary_rows = (await db.execute(secondary_stmt)).scalars().all()

    return {
        "primary_insurance": [v for v in primary_rows if v],
        "secondary_insurance": [v for v in secondary_rows if v],
    }


@router.put("/note-details", response_model=VisitDetailsOut)
async def update_note_details(
    note_id: int,
    payload: VisitDetailsUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Update visit/note details by note_id.
    Accepts editable visit columns and persists updates to visits table.
    """
    stmt = select(Visit).where(Visit.note_id == note_id)
    res = await db.execute(stmt)
    visit = res.scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail=f"Visit with note_id={note_id} not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key not in ALLOWED_UPDATE_FIELDS or not hasattr(visit, key):
            continue

        # Frontend sends empty string for cleared fields; coerce to null where valid.
        if value == "":
            current_value = getattr(visit, key, None)
            if isinstance(current_value, (bool, int, float, date, datetime)):
                value = None
            else:
                value = None

        setattr(visit, key, value)

    await db.commit()
    await db.refresh(visit)
    return visit


@router.put("/bulk-update")
async def bulk_update_note_details(
    payload: VisitBulkUpdateIn,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Bulk update allowed fields for multiple note_ids in one request.
    """
    if not payload.note_ids:
        raise HTTPException(status_code=400, detail="note_ids is required")

    note_ids = sorted({int(n) for n in payload.note_ids if n is not None})
    if not note_ids:
        raise HTTPException(status_code=400, detail="No valid note_ids provided")

    stmt = select(Visit).where(Visit.note_id.in_(note_ids))
    rows = (await db.execute(stmt)).scalars().all()
    by_note_id = {int(v.note_id): v for v in rows if v.note_id is not None}

    updates = payload.updates.model_dump(exclude_unset=True)
    applied_fields = [k for k in updates.keys() if k in ALLOWED_UPDATE_FIELDS]
    if not applied_fields:
        raise HTTPException(status_code=400, detail="No allowed update fields provided")

    updated_count = 0
    for note_id in note_ids:
        visit = by_note_id.get(note_id)
        if not visit:
            continue
        for key in applied_fields:
            value = updates[key]
            if value == "":
                value = None
            setattr(visit, key, value)
        updated_count += 1

    await db.commit()
    return {
        "requested_note_ids": len(note_ids),
        "updated_rows": updated_count,
        "applied_fields": applied_fields,
    }
