from datetime import date
from calendar import monthrange
import asyncio

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models.visits import Visit


async def count_unprepared_visits_by_month(db: AsyncSession, year: int) -> dict[int, int]:
    start_date = date(year, 1, 1)
    end_date = date(year + 1, 1, 1)

    month_expr = extract("month", Visit.note_date)

    stmt = (
        select(month_expr.label("month"), func.count().label("count"))
        .where(
            Visit.billed.is_(False),
            Visit.hold.is_(False),
            Visit.note_date >= start_date,
            Visit.note_date < end_date,
        )
        .group_by(month_expr)
        .order_by(month_expr)
    )

    result = await db.execute(stmt)
    rows = result.all()

    monthly_counts: dict[int, int] = {m: 0 for m in range(1, 13)}
    for month, count in rows:
        monthly_counts[int(month)] = int(count)

    return monthly_counts


async def count_unprepared_visits_by_day(
    db: AsyncSession,
    year: int,
    month: int,
) -> dict[int, int]:
    """
    Returns:
      { 1: count, 2: count, ..., days_in_month: count }
    Missing days default to 0.
    """

    start_date = date(year, month, 1)

    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    day_expr = extract("day", Visit.note_date)

    stmt = (
        select(
            day_expr.label("day"),
            func.count().label("count"),
        )
        .where(
            Visit.billed.is_(False),
            Visit.hold.is_(False),
            Visit.note_date >= start_date,
            Visit.note_date < end_date,
        )
        .group_by(day_expr)
        .order_by(day_expr)
    )

    result = await db.execute(stmt)
    rows = result.all()

    days_in_month = monthrange(year, month)[1]
    daily_counts: dict[int, int] = {d: 0 for d in range(1, days_in_month + 1)}

    for day, count in rows:
        daily_counts[int(day)] = int(count)

    return daily_counts


# ✅ NEW: fetch actual visits for one day (unprepared only)
async def fetch_unprepared_visits_for_day(
    db: AsyncSession,
    dt: date,
) -> list[dict]:
    """
    Returns actual visit rows for a given date (unprepared only):
      billed=false AND hold=false AND note_date = dt
    """

    # Pick columns that almost certainly exist; adjust if needed.
    stmt = (
        select(
            Visit.id.label("id"),
            Visit.note_date.label("note_date"),
            Visit.note_id.label("note_id"),  # if your model uses hn_note_id, change here
            Visit.patient_id.label("patient_id"),
            Visit.primary_insurance.label("primary_insurance"),
            Visit.visiting_therapist.label("visiting_therapist"),
            Visit.first_name.label("first_name"),
            Visit.last_name.label("last_name"),
            Visit.visit_uid.label("visit_uid"),
        )
        .where(
            Visit.billed.is_(False),
            Visit.hold.is_(False),
            Visit.note_date == dt,
        )
        .order_by(Visit.patient_id.asc(), Visit.note_id.asc())
    )

    result = await db.execute(stmt)
    rows = result.mappings().all()

    return [
        {
            "id": r.get("id"),
            "note_date": r.get("note_date"),
            "note_id": r.get("note_id"),
            "patient_id": r.get("patient_id"),
            "primary_insurance": r.get("primary_insurance") or "",
            "visiting_therapist": r.get("visiting_therapist") or "",
            "full_name": r.get("first_name", "") + ", " + r.get("last_name", "") or "",
            "visit_uid": r.get("visit_uid") or "",

            "statusBucket": "unprepared",  # matches your UI bucket key
            "arBucket": "ar",  # matches your UI AR bucket key
        }
        for r in rows
    ]


async def main():
    year = 2025  # change as needed

    async with SessionLocal() as db:
        data = await count_unprepared_visits_by_month(db, year)

        # ✅ DEMO: fetch visits for one specific day
        dt = date(2025, 11, 15)  # change as needed
        visits = await fetch_unprepared_visits_for_day(db, dt)

    print("=== Monthly counts ===")
    for m in range(1, 13):
        print(f"{year}-{m:02d}: {data[m]}")

    print("\n=== Visits for one day ===")
    print(f"date={dt.isoformat()} rows={len(visits)}")
    for v in visits[:25]:
        print(v)


if __name__ == "__main__":
    asyncio.run(main())
