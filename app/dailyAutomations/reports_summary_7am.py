import asyncio
import os
from sqlalchemy import text
from app.database import SessionLocal
from app.mondayAPI.create_monday_item import create_monday_item
from dotenv import load_dotenv

# -------------------------------------------------------------
# Load environment variables (for CHHA filtering)
# -------------------------------------------------------------
load_dotenv()

CHHA_INS = [
    x.strip().lower()
    for x in os.getenv("CHHA_INSURANCES", "").split(",")
    if x.strip()
]

# -------------------------------------------------------------
# SQL templates
# -------------------------------------------------------------
SQL_WITH_CHHA_FILTER = """
WITH today AS (
  SELECT (now() AT TIME ZONE 'America/New_York')::date AS today
)
SELECT *
FROM {table} r, today t
WHERE r.created_at::date = t.today
  AND COALESCE(r.uploaded_to_monday, false) = false
  AND lower(coalesce(r.primary_insurance, '')) != ALL(:chha)
ORDER BY r.created_at DESC
"""

SQL_NO_CHHA_FILTER = """
WITH today AS (
  SELECT (now() AT TIME ZONE 'America/New_York')::date AS today
)
SELECT *
FROM {table} r, today t
WHERE r.created_at::date = t.today
  AND COALESCE(r.uploaded_to_monday, false) = false
ORDER BY r.created_at DESC
"""


# -------------------------------------------------------------
# Main runner
# -------------------------------------------------------------
async def push_reports_to_monday():
    async with SessionLocal() as db:
        # Load all report definitions including exclude_chha
        q = await db.execute(text("""
            SELECT code, name, output_table, exclude_chha
            FROM report_definitions
            WHERE enabled = true
        """))
        defs = q.mappings().all()

        total_rows = 0

        for d in defs:
            code = d["code"]
            name = d["name"]
            table = d["output_table"]
            exclude_chha = d["exclude_chha"]

            if not table:
                continue

            print(f"🔎 Checking {name} ({code})...")

            # Choose correct SQL depending on exclude_chha flag
            if exclude_chha:
                sql_template = SQL_WITH_CHHA_FILTER
                params = {"chha": CHHA_INS}
            else:
                sql_template = SQL_NO_CHHA_FILTER
                params = {}

            sql = text(sql_template.replace("{table}", table))

            try:
                rows = (await db.execute(sql, params)).mappings().all()
            except Exception as e:
                print(f"⚠️ SQL error reading {table}: {e}")
                continue

            if not rows:
                print(f"   ➤ No new rows today in {table}")
                continue

            print(f"   ➤ Found {len(rows)} new rows — pushing to Monday...")

            for r in rows:
                try:
                    create_monday_item(
                        group_name=name,
                        therapist=r.get("visiting_therapist"),
                        note=r.get("note"),
                        note_id=r.get("note_id"),
                        case=r.get("case_description"),
                        case_id=r.get("case_id"),
                        patient_id=r.get("patient_id"),
                        patient_display_id=r.get("patient_display_id") or "",
                        first_name=r.get("first_name"),
                        last_name=r.get("last_name"),
                        cpt_code=r.get("cpt_code"),
                        note_date=str(r.get("note_date") or ""),
                    )

                    # Mark as uploaded
                    try:
                        update_sql = text(
                            f"UPDATE {table} SET uploaded_to_monday = true WHERE note_id = :note_id"
                        )
                        await db.execute(update_sql, {"note_id": r.get("note_id")})
                        await db.commit()
                    except Exception as ue:
                        print(f"⚠️ Failed to mark note {r.get('note_id')} as uploaded in {table}: {ue}")

                    total_rows += 1

                except Exception as e:
                    print(f"⚠️ Failed to send row {r.get('visit_row_id')} from {table}: {e}")

        print(f"✅ Done! {total_rows} total rows sent to Monday today.")


# -------------------------------------------------------------
# CLI entry point
# -------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(push_reports_to_monday())
