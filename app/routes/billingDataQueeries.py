from datetime import date
from datetime import date as Date, datetime
from calendar import monthrange
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.users import User
from app.dependencies.auth import get_current_user

from app.crud.billingQueries.unpreparedVisits import (
    count_unprepared_visits_by_month,
    count_unprepared_visits_by_day,
    fetch_unprepared_visits_for_day,
)

from app.crud.billingQueries.getUnproccessedAR import (
    calculate_ar_by_month,
    calculate_ar_by_day

)



router = APIRouter()


@router.get("/billing/calendar/year-summary")
async def billing_calendar_year_summary(
    year: int = Query(..., ge=2000, le=2100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns 12-month calendar summary.
    ONLY Unprepared (billed=false AND hold=false).
    """

    try:
        # ✅ delegate to CRUD
        unprepared_by_month = await count_unprepared_visits_by_month(db, year)
        ar_by_month = await calculate_ar_by_month(db, year)

        payload = []
        for month in range(1, 13):
            payload.append(
                {
                    "year": year,
                    "month": month,
                    "billing": {
                        "notReadyToBill": unprepared_by_month.get(month, 0),
                        "readyToBill": 0,
                        "billed": 0,
                        "issues": 0,
                        "paid": 0,
                        "denied": 0,
                    },
                    "reconcile": {
                        "ar": ar_by_month.get(month, 0),
                        "paid": 0,
                        "reconciled": 0,
                        "denied": 0,
                    },
                }
            )

        return payload

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build billing calendar summary: {e}",
        )


@router.get("/billing/calendar/month-summary")
async def billing_calendar_month_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Month view summary + day-by-day buckets.
    """

    try:
        # ✅ delegate to CRUD
        unprepared_by_day = await count_unprepared_visits_by_day(db, year, month)
        ar_by_day = await calculate_ar_by_day(db, year, month)

        days_in_month = monthrange(year, month)[1]
        month_total = sum(unprepared_by_day.values())

        days_payload = []
        for d in range(1, days_in_month + 1):
            days_payload.append(
                {
                    "day": d,
                    "billing": {
                        "notReadyToBill": unprepared_by_day.get(d, 0),
                        "readyToBill": 0,
                        "billed": 0,
                        "issues": 0,
                        "paid": 0,
                        "denied": 0,
                    },
                    "reconcile": {
                        "ar": ar_by_day.get(d, 0),
                        "paid": 0,
                        "reconciled": 0,
                        "denied": 0,
                    },
                }
            )

        return {
            "year": year,
            "month": month,
            "billing": {
                "notReadyToBill": month_total,
                "readyToBill": 0,
                "billed": 0,
                "issues": 0,
                "paid": 0,
                "denied": 0,
            },
            "reconcile": {
                "ar": 0,
                "paid": 0,
                "reconciled": 0,
                "denied": 0,
            },
            "days": days_payload,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build billing month summary: {e}",
        )



@router.get("/billing/calendar/day-summary")
async def billing_calendar_day_summary(
    date: str = Query(..., description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a single day summary for calendar day view.
    Includes visit rows (currently only Unprepared bucket logic).
    """
    try:
        # Parse date string safely
        dt = datetime.strptime(date, "%Y-%m-%d").date()
        year = dt.year
        month = dt.month
        day = dt.day

        # Fetch month/day maps from CRUD (your existing functions)
        unprepared_by_day = await count_unprepared_visits_by_day(db, year, month)
        ar_by_day = await calculate_ar_by_day(db, year, month)

        # ✅ Fetch actual visits for that day (rows, not counts)
        visits = await fetch_unprepared_visits_for_day(db, dt)

        return {
            "year": year,
            "month": month,
            "day": day,
            "billing": {
                "notReadyToBill": unprepared_by_day.get(day, 0),
                "readyToBill": 0,
                "billed": 0,
                "issues": 0,
                "paid": 0,
                "denied": 0,
            },
            "reconcile": {
                "ar": ar_by_day.get(day, 0),
                "paid": 0,
                "reconciled": 0,
                "denied": 0,
            },
            # ✅ NEW
            "visits": visits,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build billing day summary: {e}",
        )