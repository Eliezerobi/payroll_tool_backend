from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visits import Visit
from app.models.billing_status import BillingStatus


@dataclass
class ImportBilledResult:
    processed: int
    created_billing_status: int
    updated_visits: int
    missing_note_ids: List[int]
    duplicate_note_ids: List[int]
    already_billed_note_ids: List[int]


def _pick_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    lower_map = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        key = cand.strip().lower()
        if key in lower_map:
            return lower_map[key]
    return None


def _parse_date(val: Any) -> Optional[date]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, str) and not val.strip():
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val

    dt = pd.to_datetime(val, errors="coerce")
    return None if pd.isna(dt) else dt.date()


def parse_billed_excel(content: bytes) -> Tuple[List[Tuple[int, date]], List[int]]:
    df = pd.read_excel(BytesIO(content))

    note_col = _pick_col(df, ["note_id", "note id", "noteid"])
    if not note_col:
        raise ValueError("Excel must include a note_id column.")

    billed_date_col = _pick_col(df, ["billed_date", "bill_date", "date_billed", "date billed"])

    rows: List[Tuple[int, date]] = []
    seen: set[int] = set()
    duplicates: List[int] = []

    for _, r in df.iterrows():
        try:
            note_id = int(r.get(note_col))
        except Exception:
            continue

        if note_id in seen:
            duplicates.append(note_id)
            continue
        seen.add(note_id)

        bd = _parse_date(r.get(billed_date_col)) if billed_date_col else None
        rows.append((note_id, bd or date.today()))

    return rows, duplicates


async def import_billed_notes_from_rows(
    db: AsyncSession,
    rows: List[Tuple[int, date]],
    *,
    skip_if_already_billed: bool = True,
) -> ImportBilledResult:
    if not rows:
        return ImportBilledResult(0, 0, 0, [], [], [])

    note_ids = [nid for nid, _ in rows]

    res = await db.execute(
        select(Visit.note_id, Visit.billed).where(Visit.note_id.in_(note_ids))
    )
    existing_map: Dict[int, bool] = {int(nid): bool(billed) for nid, billed in res.all()}

    missing_note_ids = [nid for nid in note_ids if nid not in existing_map]

    created = 0
    updated = 0
    already_billed: List[int] = []

    for note_id, billed_date in rows:
        if note_id not in existing_map:
            continue
        if skip_if_already_billed and existing_map[note_id]:
            already_billed.append(note_id)
            continue

        bs = BillingStatus(
            status="Sent to Billing",
            billed_date=billed_date,
            current_note_id=note_id,
            billed_note_id=note_id,
        )
        db.add(bs)
        await db.flush()  # ensures bs.id exists

        await db.execute(
            update(Visit)
            .where(Visit.note_id == note_id)
            .values(
                billed=True,
                date_billed=billed_date,
                note_group_id=bs.id,
                billing_id=bs.id,
            )
        )

        created += 1
        updated += 1

    return ImportBilledResult(
        processed=created,
        created_billing_status=created,
        updated_visits=updated,
        missing_note_ids=missing_note_ids,
        duplicate_note_ids=[],
        already_billed_note_ids=already_billed,
    )