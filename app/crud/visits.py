import logging
from datetime import date
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from app.models.visits import Visit
from app.crud.visit_uid import (
    check_visit_conflict,
    check_same_note_date_conflict,
    get_current_year_max_uid_num,
)
from app.powerAutomate.teamsMessageMyself import notify_teams

logger = logging.getLogger(__name__)

async def insert_visit_rows(db, rows: list[dict], uploaded_by: int, batch_size: int = 500):
    """Insert visit rows safely, with Teams webhook error reporting."""
    for row in rows:
        row["uploaded_by"] = uploaded_by

    # --- Find duplicates by note_id ---
    note_ids = [r["note_id"] for r in rows if "note_id" in r]
    existing = await db.execute(select(Visit.note_id).where(Visit.note_id.in_(note_ids)))
    existing_ids = {r[0] for r in existing.all()}

    new_rows = [r for r in rows if r["note_id"] not in existing_ids]
    skipped_rows = [r for r in rows if r["note_id"] in existing_ids]

    inserted_count = 0
    uid_count = 0

    # --- Generate visit_uid ---
    current_max = await get_current_year_max_uid_num(db)
    next_num = current_max + 1
    prefix = f"{date.today().year}-"

    final_rows = []
    seen_keys = {}

    for row in new_rows:
        key = (row["patient_id"], row["case_description"], row["note_date"])

        if key in seen_keys:
            row["visit_uid"] = seen_keys[key]
            final_rows.append(row)
            continue

        same_date_uid = await check_same_note_date_conflict(db, row)
        if same_date_uid:
            row["visit_uid"] = same_date_uid
            seen_keys[key] = same_date_uid
            final_rows.append(row)
            continue

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

    # --- Insert in batches ---
    for i in range(0, len(final_rows), batch_size):
        chunk = final_rows[i : i + batch_size]
        if not chunk:
            continue

        try:
            stmt = insert(Visit).values(chunk)
            stmt = stmt.on_conflict_do_nothing(index_elements=["note_id"])
            result = await db.execute(stmt)
            inserted_count += (result.rowcount or 0)

        except Exception as e:
            message = (
                f"❌ **ERROR inserting batch into visits table**\n"
                f"**Exception:** {type(e).__name__}: {e}\n\n"
                f"**Problem row sample:**\n"
            )

            for row_index, row in enumerate(chunk[:3]):
                message += f"\n--- Row #{row_index} ---\n"
                for key, value in row.items():
                    message += f"**{key}**: `{repr(value)}`\n"

            message += "\n💡 *Check for wrong types: int in string field, bad dates, NaN, etc.*"

            notify_teams(
                status="error",
                stage="insert_visit_rows",
                message=message,
                script_name="insert_visit_rows"
            )

            raise

    await db.commit()

    # ✅ Send summary to Teams
    notify_teams(
        status="success",
        stage="insert_visit_rows",
        message=(
            f"✅ Visits Imported Successfully\n"
            f"- Inserted: {inserted_count}\n"
            f"- Skipped: {len(skipped_rows)}\n"
            f"- UIDs Created: {uid_count}"
        ),
        script_name="insert_visit_rows"
    )

    return {
        "inserted_count": inserted_count,
        "skipped_count": len(skipped_rows),
        "skipped_notes": [r["note_id"] for r in skipped_rows],
        "visit_uids_created": uid_count,
    }
