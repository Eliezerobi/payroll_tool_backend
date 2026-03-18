from __future__ import annotations

from datetime import date
from calendar import monthrange

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visits import Visit
from app.models.billing_status import BillingStatus  # adjust if needed


SENT_TO_BILLING_STATUS = "Sent to Billing"
BILLED_STATUS = "billed"


async def count_visits_by_month_for_status(
    db: AsyncSession,
    year: int,
    billing_status: str,
) -> dict[int, int]:
    """
    Returns {1..12: count} for visits where:
      - visits.billed = true
      - visits.hold = false
      - visits.billing_id -> billing_status.id
      - billing_status.status = <billing_status>
      - visit.note_date within the given year
    """
    start_date = date(year, 1, 1)
    end_date = date(year + 1, 1, 1)

    month_expr = extract("month", Visit.note_date)

    stmt = (
        select(month_expr.label("month"), func.count().label("count"))
        .select_from(Visit)
        .join(BillingStatus, Visit.billing_id == BillingStatus.id)
        .where(
            Visit.billed.is_(True),
            Visit.hold.is_(False),
            BillingStatus.status == billing_status,
            Visit.note_date >= start_date,
            Visit.note_date < end_date,
        )
        .group_by(month_expr)
        .order_by(month_expr)
    )

    rows = (await db.execute(stmt)).all()

    monthly_counts: dict[int, int] = {m: 0 for m in range(1, 13)}
    for month, count in rows:
        monthly_counts[int(month)] = int(count)

    return monthly_counts


async def count_visits_by_day_for_status(
    db: AsyncSession,
    year: int,
    month: int,
    billing_status: str,
) -> dict[int, int]:
    """
    Returns {1..days_in_month: count} for visits where:
      - visits.billed = true
      - visits.hold = false
      - billing_status.status = <billing_status>
      - visit.note_date within the given month
    Missing days default to 0.
    """
    start_date = date(year, month, 1)
    end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    day_expr = extract("day", Visit.note_date)

    stmt = (
        select(day_expr.label("day"), func.count().label("count"))
        .select_from(Visit)
        .join(BillingStatus, Visit.billing_id == BillingStatus.id)
        .where(
            Visit.billed.is_(True),
            Visit.hold.is_(False),
            BillingStatus.status == billing_status,
            Visit.note_date >= start_date,
            Visit.note_date < end_date,
        )
        .group_by(day_expr)
        .order_by(day_expr)
    )

    rows = (await db.execute(stmt)).all()

    days_in_month = monthrange(year, month)[1]
    daily_counts: dict[int, int] = {d: 0 for d in range(1, days_in_month + 1)}
    for day, count in rows:
        daily_counts[int(day)] = int(count)

    return daily_counts


async def fetch_visits_for_day_by_status(
    db: AsyncSession,
    dt: date,
    billing_status: str,
    status_bucket: str,
    ar_bucket: str = "ar",
) -> list[dict]:
    """
    Returns actual visit rows for a given date:
      billed=true AND hold=false AND billing_status.status=<billing_status> AND note_date = dt
    """
    stmt = (
        select(
            Visit.id.label("id"),
            Visit.note_date.label("note_date"),
            Visit.note_id.label("note_id"),
            Visit.patient_id.label("patient_id"),
            Visit.primary_insurance.label("primary_insurance"),
            Visit.visiting_therapist.label("visiting_therapist"),
            Visit.first_name.label("first_name"),
            Visit.last_name.label("last_name"),
            Visit.visit_uid.label("visit_uid"),
        )
        .select_from(Visit)
        .join(BillingStatus, Visit.billing_id == BillingStatus.id)
        .where(
            Visit.billed.is_(True),
            Visit.hold.is_(False),
            BillingStatus.status == billing_status,
            Visit.note_date == dt,
        )
        .order_by(Visit.patient_id.asc(), Visit.note_id.asc())
    )

    rows = (await db.execute(stmt)).mappings().all()

    return [
        {
            "id": r.get("id"),
            "note_date": r.get("note_date"),
            "note_id": r.get("note_id"),
            "patient_id": r.get("patient_id"),
            "primary_insurance": r.get("primary_insurance") or "",
            "visiting_therapist": r.get("visiting_therapist") or "",
            "full_name": (
                (r.get("first_name", "") + ", " + r.get("last_name", "")) or ""
            ).strip(", "),
            "visit_uid": r.get("visit_uid") or "",
            "statusBucket": status_bucket,
            "arBucket": ar_bucket,
        }
        for r in rows
    ]


# -----------------------------
# SENT TO BILLING wrappers
# -----------------------------

async def count_sent_to_billing_visits_by_month(db: AsyncSession, year: int) -> dict[int, int]:
    return await count_visits_by_month_for_status(db, year, SENT_TO_BILLING_STATUS)


async def count_sent_to_billing_visits_by_day(db: AsyncSession, year: int, month: int) -> dict[int, int]:
    return await count_visits_by_day_for_status(db, year, month, SENT_TO_BILLING_STATUS)


async def fetch_sent_to_billing_visits_for_day(db: AsyncSession, dt: date) -> list[dict]:
    return await fetch_visits_for_day_by_status(
        db=db,
        dt=dt,
        billing_status=SENT_TO_BILLING_STATUS,
        status_bucket="sentToBilling",
        ar_bucket="ar",
    )


# -----------------------------
# BILLED wrappers
# -----------------------------

async def count_billed_visits_by_month(db: AsyncSession, year: int) -> dict[int, int]:
    return await count_visits_by_month_for_status(db, year, BILLED_STATUS)


async def count_billed_visits_by_day(db: AsyncSession, year: int, month: int) -> dict[int, int]:
    return await count_visits_by_day_for_status(db, year, month, BILLED_STATUS)


async def fetch_billed_visits_for_day(db: AsyncSession, dt: date) -> list[dict]:
    return await fetch_visits_for_day_by_status(
        db=db,
        dt=dt,
        billing_status=BILLED_STATUS,
        status_bucket="billed",
        ar_bucket="ar",
    )


if __name__ == "__main__":
    import asyncio
    from app.database import SessionLocal

    async def _test():
        async with SessionLocal() as db:
            year = 2026
            month = 1
            dt = date(2026, 1, 1)

            print("=== Sent to Billing: by month ===")
            print(await count_sent_to_billing_visits_by_month(db, year))

            print("\n=== Sent to Billing: by day ===")
            print(await count_sent_to_billing_visits_by_day(db, year, month))

            print("\n=== Sent to Billing: visits for one day ===")
            visits = await fetch_sent_to_billing_visits_for_day(db, dt)
            print(f"date={dt.isoformat()} rows={len(visits)}")
            for v in visits[:10]:
                print(v)

            print("\n=== Billed: by month ===")
            print(await count_billed_visits_by_month(db, year))

            print("\n=== Billed: by day ===")
            print(await count_billed_visits_by_day(db, year, month))

            print("\n=== Billed: visits for one day ===")
            visits = await fetch_billed_visits_for_day(db, dt)
            print(f"date={dt.isoformat()} rows={len(visits)}")
            for v in visits[:10]:
                print(v)

    asyncio.run(_test())