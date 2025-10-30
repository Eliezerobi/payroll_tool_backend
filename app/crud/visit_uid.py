from datetime import date
from sqlalchemy import select, func, cast, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.visits import Visit


async def check_visit_conflict(db: AsyncSession, row: dict) -> str | None:
    """
    Check if this exact note already exists.
    If found, return the existing visit_uid, else None.
    """
    stmt = (
        select(Visit.visit_uid)
        .where(
            (Visit.patient_id == row["patient_id"]) &
            (Visit.case_description == row["case_description"]) &
            (Visit.note_number == row.get("note_number"))
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def check_same_note_date_conflict(db: AsyncSession, row: dict) -> str | None:
    """
    Check if there is already a visit with the same patient_id,
    case_description, and case_date.
    Returns the existing visit_uid if found, otherwise None.
    """
    stmt = (
        select(Visit.visit_uid)
        .where(
            (Visit.patient_id == row["patient_id"]) &
            (Visit.case_description == row["case_description"]) &
            (Visit.case_date == row["note_date"])
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_current_year_max_uid_num(db: AsyncSession) -> int:
    year = date.today().year
    prefix = f"{year}-"
    result = await db.execute(
        select(func.max(cast(func.substr(Visit.visit_uid, 6), Integer)))
        .where(Visit.visit_uid.like(f"{prefix}%"))
    )
    return result.scalar_one_or_none() or 0