from sqlalchemy import text

async def ensure_report_table_exists(db, definition):
    table = definition.output_table
    cols = definition.output_columns["columns"]

    # 1. CREATE TABLE IF NOT EXISTS (basic skeleton)
    base_columns = """
        id SERIAL PRIMARY KEY,
        created_at TIMESTAMP DEFAULT NOW()
    """

    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {table} (
        {base_columns}
    );
    """

    await db.execute(text(create_sql))
    await db.commit()

    # 2. Get existing columns from database
    existing_cols_query = text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :table
    """)

    result = await db.execute(existing_cols_query, {"table": table.lower()})

    existing = {row[0] for row in result.fetchall()}

    # 3. Add missing columns as ALTER TABLE statements
    for col in cols:
        name = col["name"]
        col_type = col["type"]

        if name not in existing:
            alter_sql = text(f"ALTER TABLE {table} ADD COLUMN {name} {col_type};")
            await db.execute(alter_sql)

    await db.commit()

if __name__ == "__main__":
    import asyncio
    from app.database import SessionLocal

    from sqlalchemy import text

    async def main():
        async with SessionLocal() as db:
            # Load a test report
            q = await db.execute(text("SELECT * FROM report_definitions WHERE code = 'rpt_97750CPT'"))
            definition = q.mappings().first()

            if not definition:
                print("❌ test_report not found in report_definitions")
                return

            await ensure_report_table_exists(db, definition)
            print("✅ Table synced:", definition["output_table"])

    asyncio.run(main())