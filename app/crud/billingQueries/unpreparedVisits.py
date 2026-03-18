from __future__ import annotations

import asyncio
import re
from calendar import monthrange
from datetime import date
from typing import List

from sqlalchemy import and_, case, extract, func, or_, select, false, not_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models.patients import Patient
from app.models.visits import Visit

BUCKETS = ("unprepared", "held_for_deductible", "ready_to_bill")


# Put your actual disallowed diagnosis values here (exact matches)
DISALLOWED_DIAGNOSES = [
    "G35",
    "E08.37",
]

def diagnosis_has_any_blocked_code_expr():
    """
    True if Visit.diagnosis contains ANY blocked code as a token.
    Uses Postgres regex (~*) for case-insensitive match with boundaries.
    Boundary: start/end or non-alphanumeric around the code.
    """
    if not DISALLOWED_DIAGNOSES:
        return false()  # no blocked codes => never matches

    patterns = []
    for code in DISALLOWED_DIAGNOSES:
        c = (code or "").strip()
        if not c:
            continue
        esc = re.escape(c)
        # token boundary: not A-Z0-9 or dot on both sides
        # allows punctuation/space/commas around codes like "G35", "E08.37"
        patterns.append(rf"(^|[^A-Za-z0-9\.]){esc}($|[^A-Za-z0-9\.])")

    if not patterns:
        return false()

    combined = "(" + "|".join(patterns) + ")"
    return Visit.diagnosis.op("~*")(combined)  # Postgres case-insensitive regex


def passes_abc_expr():
    primary_ok = and_(
        Visit.primary_insurance.is_not(None),
        Visit.primary_insurance != "",
        Visit.primary_insurance.contains("|"),
    )

    secondary_ok = or_(
        Visit.secondary_insurance.is_(None),
        Visit.secondary_insurance == "",
        Visit.secondary_insurance.contains("|"),
    )

    blocked_hit = diagnosis_has_any_blocked_code_expr()

    # passes if BOTH diagnosis fields are empty/null,
    # OR (at least one is non-empty AND no blocked code hit)
    diagnosis_ok = and_(
        Visit.diagnosis.is_not(None),
        Visit.diagnosis != "",
        Visit.medical_diagnosis.is_not(None),
        Visit.medical_diagnosis != "",
        not_(blocked_hit),
    )

    return and_(primary_ok, secondary_ok, diagnosis_ok)

def status_bucket_expr():
    """
    Buckets:
      - unprepared: fails A/B/C
      - ready_to_bill: passes A/B/C AND (note_date year < 2026 OR patient.met_deductible = true)
      - held_for_deductible: passes A/B/C AND note_date year >= 2026 AND patient.met_deductible is not true
    """
    passes_abc = passes_abc_expr()
    note_year = extract("year", Visit.note_date)

    return case(
        # fails A/B/C
        (passes_abc.is_(False), "unprepared"),

        # passes A/B/C AND note_date year is before 2026 => treat as deductible met
        (note_year < 2026, "ready_to_bill"),

        # passes A/B/C AND note_date year >= 2026 AND met_deductible true
        (Patient.met_deductible.is_(True), "ready_to_bill"),

        # otherwise (passes A/B/C, year >= 2026, not met) => held
        else_="held_for_deductible",
    ).label("status_bucket")


async def count_visits_by_month_three_buckets(db: AsyncSession, year: int) -> dict[int, dict[str, int]]:
    start_date = date(year, 1, 1)
    end_date = date(year + 1, 1, 1)

    month_expr = extract("month", Visit.note_date).label("month")
    bucket = status_bucket_expr()

    stmt = (
        select(
            month_expr,
            bucket,
            func.count().label("count"),
        )
        .select_from(Visit)
        .outerjoin(Patient, Patient.id == Visit.patient_id)
        .where(
            Visit.billed.is_(False),
            Visit.hold.is_(False),
            Visit.note_date >= start_date,
            Visit.note_date < end_date,
        )
        .group_by(month_expr, bucket)
        .order_by(month_expr, bucket)
    )

    result = await db.execute(stmt)
    rows = result.all()

    out: dict[int, dict[str, int]] = {
        m: {b: 0 for b in BUCKETS} for m in range(1, 13)
    }

    for month, bucket_name, count in rows:
        out[int(month)][str(bucket_name)] = int(count)

    return out



async def count_visits_by_day_three_buckets(
    db: AsyncSession,
    year: int,
    month: int,
) -> dict[int, dict[str, int]]:
    start_date = date(year, month, 1)
    end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    day_expr = extract("day", Visit.note_date).label("day")
    bucket = status_bucket_expr()

    stmt = (
        select(
            day_expr,
            bucket,
            func.count().label("count"),
        )
        .select_from(Visit)
        .outerjoin(Patient, Patient.id == Visit.patient_id)
        .where(
            Visit.billed.is_(False),
            Visit.hold.is_(False),
            Visit.note_date >= start_date,
            Visit.note_date < end_date,
        )
        .group_by(day_expr, bucket)
        .order_by(day_expr, bucket)
    )

    result = await db.execute(stmt)
    rows = result.all()

    dim = monthrange(year, month)[1]
    out: dict[int, dict[str, int]] = {
        d: {b: 0 for b in BUCKETS} for d in range(1, dim + 1)
    }

    for day, bucket_name, count in rows:
        out[int(day)][str(bucket_name)] = int(count)

    return out

async def fetch_visits_for_day_three_buckets(db: AsyncSession, dt: date) -> List[dict]:
    """
    3 buckets for visits on dt (only billed=false & hold=false):
    - unprepared: fails ANY of A/B/C
    - ready_to_bill: passes A/B/C AND (year(note_date) < 2026 OR patient.met_deductible = true)
    - held_for_deductible: passes A/B/C AND year(note_date) >= 2026 AND patient.met_deductible is not true
    """
    bucket_expr = status_bucket_expr()

    stmt = (
        select(
            Visit.id.label("id"),
            Visit.note_date.label("note_date"),
            Visit.note_id.label("note_id"),
            Visit.patient_id.label("patient_id"),
            Visit.primary_insurance.label("primary_insurance"),
            Visit.secondary_insurance.label("secondary_insurance"),
            Visit.diagnosis.label("diagnosis"),
            Visit.visiting_therapist.label("visiting_therapist"),
            Visit.first_name.label("first_name"),
            Visit.last_name.label("last_name"),
            Visit.visit_uid.label("visit_uid"),
            Patient.met_deductible.label("met_deductible"),
            bucket_expr,
        )
        .select_from(Visit)
        .outerjoin(Patient, Patient.id == Visit.patient_id)
        .where(
            Visit.billed.is_(False),
            Visit.hold.is_(False),
            Visit.note_date == dt,
        )
        .order_by(Visit.patient_id.asc(), Visit.note_id.asc())
    )

    result = await db.execute(stmt)
    rows = result.mappings().all()

    out: List[dict] = []
    for r in rows:
        first = (r.get("first_name") or "").strip()
        last = (r.get("last_name") or "").strip()
        full_name = f"{first} {last}".strip()

        out.append(
            {
                "id": r.get("id"),
                "note_date": r.get("note_date"),
                "note_id": r.get("note_id"),
                "patient_id": r.get("patient_id"),
                "primary_insurance": r.get("primary_insurance") or "",
                "secondary_insurance": r.get("secondary_insurance") or "",
                "diagnosis": r.get("diagnosis") or "",
                "visiting_therapist": r.get("visiting_therapist") or "",
                "full_name": full_name,
                "visit_uid": r.get("visit_uid") or "",
                "met_deductible": (
                    bool(r.get("met_deductible")) if r.get("met_deductible") is not None else None
                ),
                "statusBucket": r.get("status_bucket"),
                "arBucket": "ar",
            }
        )

    return out


async def main():
    year = 2026

    async with SessionLocal() as db:
        monthly = await count_visits_by_month_three_buckets(db, year)

        dt = date(2025, 11, 15)
        visits = await fetch_visits_for_day_three_buckets(db, dt)

    print("=== Monthly counts ===")
    for m in range(1, 13):
        print(f"{year}-{m:02d}: {monthly[m]}")

    print("\n=== Visits for one day (3 buckets) ===")
    print(f"date={dt.isoformat()} rows={len(visits)}")
    for v in visits[:25]:
        print(v)


if __name__ == "__main__":
    asyncio.run(main())


# fetch_unprepared_visits_for_day