from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import cast, String, or_
from typing import Optional, Sequence

from app.database import get_db
from app.models.users import User
from app.models.visits import Visit
from app.dependencies.auth import get_current_user

router = APIRouter()

@router.get("/payroll/history")
async def get_payroll_history(
    query: Optional[str] = Query(None, description="Search by patient_id, name, or invoice"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),  # 🔐 Requires valid login
):
    """
    Return visit history with limited fields.
    If login expired → 401 Unauthorized.
    """

    stmt = select(Visit)

    # 🔍 Search support
    if query:
        like_pattern = f"%{query}%"
        stmt = stmt.where(
            or_(
                cast(Visit.patient_id, String).ilike(like_pattern),
                Visit.first_name.ilike(like_pattern),
                Visit.last_name.ilike(like_pattern)
            )
        )

    result = await db.execute(stmt)
    visits: Sequence[Visit] = result.scalars().all()

    return [
        {
            "visit_uid": v.visit_uid,
            "id": v.id,
            "patient_id": v.patient_id,
            "first_name": v.first_name,
            "last_name": v.last_name,
            "note": v.note,
            "note_date": str(v.note_date) if v.note_date else None,
            "visit_type": v.visit_type,
            "case_description": v.case_description,
            "note_number": v.note_number,
            "visiting_therapist":v.visiting_therapist,
            "supervising_therapist":str(v.supervising_therapist) if v.supervising_therapist else None,
        }
        for v in visits
    ]
