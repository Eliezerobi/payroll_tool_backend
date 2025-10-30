# insert_visits.py
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from app.models.visits import Visit
from app.crud.visit_uid import check_visit_conflict, check_same_note_date_conflict, get_current_year_max_uid_num
from datetime import date

async def insert_visit_rows(db, rows: list[dict], uploaded_by: int, batch_size: int = 500):
    for row in rows:
        row["uploaded_by"] = uploaded_by

    note_ids = [r["note_id"] for r in rows if "note_id" in r]
    existing = await db.execute(select(Visit.note_id).where(Visit.note_id.in_(note_ids)))
    existing_ids = {r[0] for r in existing.all()}

    new_rows = [r for r in rows if r["note_id"] not in existing_ids]
    skipped_rows = [r for r in rows if r["note_id"] in existing_ids]

    inserted_count = 0
    uid_count = 0

    # Fetch max ONCE, then increment locally
    current_max = await get_current_year_max_uid_num(db)
    next_num = current_max + 1
    year = date.today().year
    prefix = f"{year}-"

    final_rows = []
    seen_keys = {}  # (patient_id, case_description, case_date) -> visit_uid

    for row in new_rows:
        key = (row["patient_id"], row["case_description"], row["note_date"])

        # ✅ Check same-case-date conflicts already in final_rows
        if key in seen_keys:
            row["visit_uid"] = seen_keys[key]
            final_rows.append(row)
            continue

        # ✅ Check DB for an existing UID
        same_date_uid = await check_same_note_date_conflict(db, row)
        if same_date_uid:
            row["visit_uid"] = same_date_uid
            seen_keys[key] = same_date_uid
            final_rows.append(row)
            continue

        # ✅ Check for note_id/note conflict
        existing_uid = await check_visit_conflict(db, row)
        if existing_uid:
            row["visit_uid"] = existing_uid
            seen_keys[key] = existing_uid
        else:
            row["visit_uid"] = f"{prefix}{next_num:06d}"
            seen_keys[key] = row["visit_uid"]
            next_num += 1
            uid_count += 1

        final_rows.append(row)

    for i in range(0, len(final_rows), batch_size):
        chunk = final_rows[i:i + batch_size]
        if not chunk:
            continue
        stmt = insert(Visit).values(chunk)
        stmt = stmt.on_conflict_do_nothing(index_elements=["note_id"])
        result = await db.execute(stmt)
        inserted_count += (result.rowcount or 0)

    await db.commit()
    return {
        "inserted_count": inserted_count,
        "skipped_count": len(skipped_rows),
        "skipped_notes": [r["note_id"] for r in skipped_rows],
        "visit_uids_created": uid_count,
    }
