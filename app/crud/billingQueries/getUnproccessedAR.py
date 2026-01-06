from __future__ import annotations

from datetime import date
from calendar import monthrange
from typing import Dict
import asyncio

from sqlalchemy import select, func, extract, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models.visits import Visit


# ----------------------------
# AR RATE RULES
# ----------------------------
def ar_rate_case():
    """
    primary_insurance:
      americare = 110
      'royal care', 'extendedcare', 'able health' = 105
      any other (including NULL/blank) = 104
    """
    ins = func.lower(func.trim(Visit.primary_insurance))

    return case(
        (ins == "americare", 110),
        (ins.in_(["royal care", "extendedcare", "able health"]), 105),
        else_=104,
    )


# ----------------------------
# AR AGGREGATIONS
# ----------------------------
async def calculate_ar_by_month(
    db: AsyncSession, year: int
) -> Dict[int, int]:
    start_date = date(year, 1, 1)
    end_date = date(year + 1, 1, 1)

    month_expr = extract("month", Visit.note_date)
    ar_expr = ar_rate_case()

    stmt = (
        select(
            month_expr.label("month"),
            func.sum(ar_expr).label("ar"),
        )
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

    monthly_ar: Dict[int, int] = {m: 0 for m in range(1, 13)}
    for month, ar in rows:
        monthly_ar[int(month)] = int(ar or 0)

    return monthly_ar


async def calculate_ar_by_day(
    db: AsyncSession, year: int, month: int
) -> Dict[int, int]:
    start_date = date(year, month, 1)
    end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    day_expr = extract("day", Visit.note_date)
    ar_expr = ar_rate_case()

    stmt = (
        select(
            day_expr.label("day"),
            func.sum(ar_expr).label("ar"),
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
    daily_ar: Dict[int, int] = {d: 0 for d in range(1, days_in_month + 1)}
    for day, ar in rows:
        daily_ar[int(day)] = int(ar or 0)

    return daily_ar


# ----------------------------
# __main__
# ----------------------------
async def main(year, month):

    async with SessionLocal() as db:
        monthly_ar = await calculate_ar_by_month(db, year)
        daily_ar = await calculate_ar_by_day(db, year, month)

    print(f"\nAR by month ({year}):")
    for m in range(1, 13):
        print(f"{year}-{m:02d}: ${monthly_ar[m]}")

    print(f"\nAR by day ({year}-{month:02d}):")
    for d, ar in daily_ar.items():
        print(f"Day {d}: ${ar}")


if __name__ == "__main__":
    year = 2025
    month = 11
    asyncio.run(main(year, month))
