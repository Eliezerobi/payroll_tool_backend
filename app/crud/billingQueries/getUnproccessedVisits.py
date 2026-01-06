from __future__ import annotations

from datetime import date as Date
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visits import Visit
from app.models.patients import Patient


async def fetch_day_visits(db: AsyncSession, dt: Date) -> List[dict]:
    """
    Returns the actual visit rows for a given date.

    Matches calendar logic:
    - billed = false
    - hold = false
    """

    stmt = (
        select(
            Visit.note_id.label("note_id"),
            Visit.dos.label("dos"),
            Visit.primary_insurance.label("insurance"),
            Patient.first_name.label("first_name"),
            Patient.last_name.label("last_name"),
        )
        .select_from(Visit)
        .join(Patient, Patient.id == Visit.patient_id)
        .where(Visit.dos == dt)
        .where(Visit.billed.is_(False))
        .where(Visit.hold.is_(False))
        .order_by(
            Patient.last_name.asc(),
            Patient.first_name.asc(),
            Visit.note_id.asc(),
        )
    )

    res = await db.execute(stmt)
    rows = res.mappings().all()

    out: List[dict] = []
    for r in rows:
        first = (r.get("first_name") or "").strip()
        last = (r.get("last_name") or "").strip()
        patient = f"{first} {last}".strip() or "Unknown"

        out.append(
            {
                "noteId": r["note_id"],
                "patient": patient,
                "dos": r["dos"],
                "insurance": r.get("insurance") or "",
                "status": "",
                "bucket": "notReadyToBill",
            }
        )

    return out
