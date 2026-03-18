from datetime import date
from datetime import date as Date, datetime
from calendar import monthrange
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.users import User
from app.dependencies.auth import get_current_user

from app.crud.billingQueries.unpreparedVisits import (
    count_visits_by_month_three_buckets,
    count_visits_by_day_three_buckets,
    fetch_visits_for_day_three_buckets,
)


from app.crud.billingQueries.getUnproccessedAR import (
    calculate_ar_by_month,
    calculate_ar_by_day

)

from app.crud.billingQueries.sentToBillingVisits import (
    count_sent_to_billing_visits_by_month,
    count_sent_to_billing_visits_by_day,
    fetch_sent_to_billing_visits_for_day,
    count_billed_visits_by_month,
    count_billed_visits_by_day,
    fetch_billed_visits_for_day,
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
    Unbilled (billed=false AND hold=false).
    """

    try:
        # ✅ delegate to CRUD
        by_month = await count_visits_by_month_three_buckets(db, year)
        sent_to_billing_by_month = await count_sent_to_billing_visits_by_month(db, year)
        billed_by_month = await count_billed_visits_by_month(db, year)
        ar_by_month = await calculate_ar_by_month(db, year)

        payload = []
        for month in range(1, 13):
            m_counts = by_month.get(month, {})
            unprepared = m_counts.get("unprepared", 0)
            held = m_counts.get("held_for_deductible", 0)
            ready = m_counts.get("ready_to_bill", 0)
            payload.append(
                {
                    "year": year,
                    "month": month,
                    "billing": {
                        "notReadyToBill": unprepared,
                        "heldForDeductible": held,
                        "readyToBill": ready,
                        "sentToBilling": sent_to_billing_by_month.get(month, 0),
                        "billed": billed_by_month.get(month, 0),
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
        by_day = await count_visits_by_day_three_buckets(db, year, month)
        sent_to_billing_by_day = await count_sent_to_billing_visits_by_day(db, year, month)
        billed_by_day = await count_billed_visits_by_day(db, year, month)
        ar_by_day = await calculate_ar_by_day(db, year, month)

        days_in_month = monthrange(year, month)[1]
        unprepared_month_total = sum(v.get("unprepared", 0) for v in by_day.values())
        held_month_total = sum(v.get("held_for_deductible", 0) for v in by_day.values())
        ready_month_total = sum(v.get("ready_to_bill", 0) for v in by_day.values())
        sent_to_billing_month_total = sum(sent_to_billing_by_day.values())
        billed_month_total = sum(billed_by_day.values())


        days_payload = []
        for d in range(1, days_in_month + 1):
            d_counts = by_day.get(d, {})
            days_payload.append(
                {
                    "day": d,
                    "billing": {
                        "notReadyToBill": d_counts.get("unprepared", 0),
                        "heldForDeductible": d_counts.get("held_for_deductible", 0),
                        "readyToBill": d_counts.get("ready_to_bill", 0),
                        "sentToBilling": sent_to_billing_by_day.get(d, 0),
                        "billed": billed_by_day.get(d, 0),
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
                "notReadyToBill": unprepared_month_total,
                "heldForDeductible": held_month_total,
                "readyToBill": ready_month_total,
                "sentToBilling": sent_to_billing_month_total,
                "billed": billed_month_total,
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
        by_day = await count_visits_by_day_three_buckets(db, year, month)
        day_counts = by_day.get(day, {})

        sent_to_billing_by_day = await count_sent_to_billing_visits_by_day(db, year, month)
        ar_by_day = await calculate_ar_by_day(db, year, month)

        three_bucket_visits = await fetch_visits_for_day_three_buckets(db, dt)
        sent_visits = await fetch_sent_to_billing_visits_for_day(db, dt)
        billed_by_day = await count_billed_visits_by_day(db, year, month)
        billed_visits = await fetch_billed_visits_for_day(db, dt)
        visits = three_bucket_visits + sent_visits + billed_visits


        return {
            "year": year,
            "month": month,
            "day": day,
            "billing": {
                "notReadyToBill": day_counts.get("unprepared", 0),
                "heldForDeductible": day_counts.get("held_for_deductible", 0),
                "readyToBill": day_counts.get("ready_to_bill", 0),
                "sentToBilling": sent_to_billing_by_day.get(day, 0),
                "billed": billed_by_day.get(day, 0),
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