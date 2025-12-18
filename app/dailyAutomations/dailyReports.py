from sqlalchemy import text
from app.database import SessionLocal
from app.reports.dynamicTableCreator import ensure_report_table_exists
from app.powerAutomate.teamsMessageMyself import notify_teams
import pathlib
from datetime import datetime

async def run_all_reports():

    reports_dir = pathlib.Path(__file__).resolve().parent.parent / "reports"

    async with SessionLocal() as db:

        q = await db.execute(text("SELECT * FROM report_definitions WHERE enabled = true"))
        reports = q.mappings().all()

        for r in reports:

            report_code = r["code"]
            sql_file = r["sql_file"]
            table_name = r["output_table"]
            sql_path = reports_dir / sql_file

            # ✅ STEP A: ensure table exists / updated
            try:
                await ensure_report_table_exists(db, r)

                notify_teams(
                    status="success",
                    stage="report",
                    script_name=None,
                    message=(
                        f"✅ [{report_code}] ensure_table\n"
                        f"Table `{table_name}` verified or updated.\n"
                        f"SQL: {sql_file}\n"
                        f"Time: {datetime.now()}"
                    )
                )

            except Exception as e:

                notify_teams(
                    status="error",
                    stage="report",
                    script_name=None,
                    message=(
                        f"❌ [{report_code}] ensure_table FAILED\n"
                        f"Report table: `{table_name}`\n"
                        f"SQL: {sql_file}\n"
                        f"Error: {e}\n"
                        f"Time: {datetime.now()}"
                    )
                )
                continue

            # ✅ STEP B: check SQL file exists
            if not sql_path.exists():

                notify_teams(
                    status="error",
                    stage="report",
                    script_name=None,
                    message=(
                        f"❌ [{report_code}] SQL FILE NOT FOUND\n"
                        f"Missing file: {sql_file}\n"
                        f"Expected at: {sql_path}\n"
                        f"Time: {datetime.now()}"
                    )
                )
                continue

            # ✅ STEP C: execute SQL
            try:
                sql_script = sql_path.read_text()

                await db.execute(text(sql_script))
                await db.commit()

                notify_teams(
                    status="success",
                    stage="report",
                    script_name=None,
                    message=(
                        f"✅ [{report_code}] executed\n"
                        f"Ran SQL file: {sql_file}\n"
                        f"Inserted/updated rows successfully.\n"
                        f"Time: {datetime.now()}"
                    )
                )

            except Exception as e:

                notify_teams(
                    status="error",
                    stage="report",
                    script_name=None,
                    message=(
                        f"❌ [{report_code}] EXECUTION FAILED\n"
                        f"SQL file: {sql_file}\n"
                        f"Error: {e}\n"
                        f"Time: {datetime.now()}"
                    )
                )
                continue

    # ✅ Final message
    notify_teams(
        status="success",
        stage="report",
        script_name=None,
        message=(
            "✅ Finished running ALL reports.\n"
            f"Time: {datetime.now()}"
        )
    )


# Allow running standalone
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_all_reports())
