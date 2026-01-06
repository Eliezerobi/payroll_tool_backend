from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.users import User
from app.models.visits import Visit  # <-- adjust to your actual model import
from app.schemas.visits import VisitDetailsOut

router = APIRouter(prefix="/visits", tags=["Visits"])


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
