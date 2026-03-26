from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime, timezone, date
from decimal import Decimal, InvalidOperation
import pandas as pd
from io import BytesIO
import re
import json
import math

from app.database import get_db
from app.models.millin_invoices import MillinInvoice

router = APIRouter(prefix="/millin-invoices", tags=["Millin Invoices"])


INTEGER_COLS = {
    "actual_invoice_id",
    "patient_id",
    "num_procs",
}

STRING_ID_COLS = {
    "medical_record_id",
    "transaction_control_number",
    "claim_identifier",
    "policy_number",
    "source_system_identifier",
    "rate_code",
    "insurance_payer_id",
    "payer_category_id",
    "program_type_id",
    "file_number",
    "patient_full_name",
    "originating_invoice_status",
    "final_invoice_status",
    "invoice_status_description",
    "revenue_code_summary",
    "location_summary",
    "provider_summary",
    "diagnosis_summary",
    "procedure_summary",
    "claim_procedure_summary",
    "over_90_day_reason",
    "claim_reason_code_summary",
    "claim_remark_code_summary",
    "av_indicator",
    "issue_tracker_status",
    "issue_tracker_category_description",
    "note_color",
}

DECIMAL_COLS = {
    "charge_summary",
    "payment_summary",
    "adjustment_summary",
    "invoice_balance",
}

DATE_COLS = {
    "invoice_date",
    "date_of_service",
    "date_of_service_thru",
}

BOOL_COLS = {
    "has_note",
}

PRIMARY_CHECK_COLS = {
    "invoice_status_description",
    "payment_summary",
}


def to_snake(name: str) -> str:
    s = str(name).strip()
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"__+", "_", s)
    return s.lower()


def normalize_value(col: str, val, invalid_counts: dict | None = None):
    if pd.isna(val):
        return None

    if isinstance(val, pd.Timestamp):
        val = val.to_pydatetime()

    if col in DATE_COLS:
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        try:
            parsed = pd.to_datetime(val, errors="coerce")
            if pd.isna(parsed):
                if invalid_counts is not None:
                    invalid_counts[col] = invalid_counts.get(col, 0) + 1
                return None
            return parsed.date()
        except Exception:
            if invalid_counts is not None:
                invalid_counts[col] = invalid_counts.get(col, 0) + 1
            return None

    if col == "has_note":
        if isinstance(val, str):
            v = val.strip().upper()
            if v == "Y":
                return True
            if v == "N":
                return False
            if v == "":
                return None
        if isinstance(val, bool):
            return val
        if invalid_counts is not None:
            invalid_counts[col] = invalid_counts.get(col, 0) + 1
        return None

    if col in INTEGER_COLS:
        try:
            if isinstance(val, str):
                val = val.strip()
                if val == "":
                    return None
            return int(float(val))
        except (TypeError, ValueError):
            if invalid_counts is not None:
                invalid_counts[col] = invalid_counts.get(col, 0) + 1
            return None

    if col in DECIMAL_COLS:
        try:
            s = str(val).strip()
            if s == "":
                return None
            return Decimal(s)
        except (InvalidOperation, AttributeError, ValueError):
            if invalid_counts is not None:
                invalid_counts[col] = invalid_counts.get(col, 0) + 1
            return None

    if col in STRING_ID_COLS:
        if isinstance(val, str):
            val = val.strip()
            return val if val != "" else None
        return str(val)

    if isinstance(val, str):
        val = val.strip()
        return val if val != "" else None

    return val


def comparable_value(col: str, val):
    val = normalize_value(col, val)

    if val is None:
        return None

    if col in DATE_COLS:
        if isinstance(val, datetime):
            return val.date()
        return val

    if col in DECIMAL_COLS:
        try:
            return Decimal(str(val))
        except Exception:
            return val

    if col == "has_note":
        return bool(val) if val is not None else None

    if col in INTEGER_COLS:
        try:
            return int(val)
        except Exception:
            return val

    return val


def json_safe_value(col: str, val):
    if val is None:
        return None

    if col in DATE_COLS:
        if isinstance(val, datetime):
            return val.date().isoformat()
        if isinstance(val, date):
            return val.isoformat()
        return str(val)

    if col in DECIMAL_COLS:
        return str(val)

    if isinstance(val, Decimal):
        return str(val)

    if isinstance(val, (datetime, date)):
        return val.isoformat()

    if isinstance(val, float) and math.isnan(val):
        return None

    return val


def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def postgres_cast_for_col(col: str) -> str:
    if col in INTEGER_COLS:
        return "bigint"
    if col in DECIMAL_COLS:
        return "numeric"
    if col in DATE_COLS:
        return "date"
    if col in BOOL_COLS:
        return "boolean"
    return "text"


@router.post("/import")
async def import_millin_invoices(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    print("\n==================== START MILLIN IMPORT ====================")
    print(f"[import] filename={file.filename!r}")

    contents = await file.read()
    print(f"[import] file size bytes={len(contents)}")

    try:
        df = pd.read_excel(BytesIO(contents), dtype=object)
    except Exception as e:
        print(f"[import] Failed reading Excel: {e}")
        raise HTTPException(status_code=400, detail=f"Could not read Excel file: {str(e)}")

    original_row_count = len(df)

    print(f"[import] raw columns={list(df.columns)}")
    print(f"[import] raw row count={original_row_count}")

    df.columns = [to_snake(c) for c in df.columns]
    print(f"[import] normalized columns={list(df.columns)}")

    if "actual_invoice_id" not in df.columns:
        print("[import] ERROR: actual_invoice_id column missing after normalization")
        raise HTTPException(
            status_code=400,
            detail=f"Missing 'ActualInvoiceID' column. Normalized columns found: {list(df.columns)}",
        )

    now = datetime.now(timezone.utc)

    inserted = 0
    updated = 0
    skipped = 0
    matched_existing = 0
    checked_not_updated = 0

    allowed_cols = {c.name for c in MillinInvoice.__table__.columns}
    excel_cols = set(df.columns)
    valid_cols = sorted(excel_cols.intersection(allowed_cols))
    skipped_excel_cols = sorted(excel_cols - allowed_cols)

    print(f"[import] model columns={sorted(allowed_cols)}")
    print(f"[import] valid import columns={valid_cols}")
    print(f"[import] skipped excel columns={skipped_excel_cols}")

    invalid_counts = {}

    for col in valid_cols:
        df[col] = df[col].apply(lambda v, c=col: normalize_value(c, v, invalid_counts))

    if invalid_counts:
        print(f"[normalize] invalid conversion counts={invalid_counts}")

    invalid_id_mask = df["actual_invoice_id"].isna()
    invalid_id_count = int(invalid_id_mask.sum())
    skipped += invalid_id_count

    df = df[~invalid_id_mask].copy()

    before_dedupe = len(df)
    df = df.drop_duplicates(subset=["actual_invoice_id"], keep="last").copy()
    deduped_out = before_dedupe - len(df)
    skipped += deduped_out

    ids = df["actual_invoice_id"].tolist()

    print(f"[import] cleaned valid invoice ids count={len(ids)}")
    print(f"[import] sample cleaned ids={ids[:10]}")
    print(f"[import] skipped invalid ids={invalid_id_count}")
    print(f"[import] skipped duplicate ids in upload={deduped_out}")

    if not ids:
        print("[import] No valid invoice IDs found. Exiting.")
        return {
            "inserted": 0,
            "updated": 0,
            "matched_existing": 0,
            "checked_not_updated": 0,
            "skipped": skipped,
            "total_rows": original_row_count,
            "invalid_conversion_counts": invalid_counts,
        }

    print("[import] querying existing rows...")
    existing_rows = await db.execute(
        select(MillinInvoice).where(MillinInvoice.actual_invoice_id.in_(ids))
    )
    existing_objects = existing_rows.scalars().all()

    existing_map = {row.actual_invoice_id: row for row in existing_objects}
    existing_ids = set(existing_map.keys())

    print(f"[import] existing ids found count={len(existing_map)}")
    print(f"[import] sample existing ids={list(existing_map.keys())[:10]}")

    df_new = df[~df["actual_invoice_id"].isin(existing_ids)].copy()
    df_existing = df[df["actual_invoice_id"].isin(existing_ids)].copy()

    inserted = len(df_new)
    matched_existing = len(df_existing)

    print(f"[import] new rows count={len(df_new)}")
    print(f"[import] existing rows count={len(df_existing)}")

    if not df_new.empty:
        insert_records = []

        for row in df_new.to_dict(orient="records"):
            record = {
                "actual_invoice_id": row["actual_invoice_id"],
                "created_at": now,
                "updated_at": now,
                "checked_at": now,
            }

            for col in valid_cols:
                if col == "actual_invoice_id":
                    continue
                record[col] = row.get(col)

            insert_records.append(record)

        print(f"[insert] bulk inserting {len(insert_records)} rows")
        await db.execute(pg_insert(MillinInvoice), insert_records)

    update_records = []
    checked_only_ids = []

    if not df_existing.empty:
        records_existing = df_existing.to_dict(orient="records")

        for row in records_existing:
            actual_invoice_id = row["actual_invoice_id"]
            existing = existing_map[actual_invoice_id]

            primary_changed = False
            for col in PRIMARY_CHECK_COLS:
                if col not in valid_cols:
                    continue

                new_val = comparable_value(col, row.get(col))
                old_val = comparable_value(col, getattr(existing, col, None))

                if new_val != old_val:
                    primary_changed = True
                    break

            if not primary_changed:
                checked_only_ids.append(actual_invoice_id)
                continue

            update_row = {"actual_invoice_id": actual_invoice_id}

            for col in valid_cols:
                if col == "actual_invoice_id":
                    continue
                update_row[col] = row.get(col)

            update_records.append(update_row)

    checked_not_updated = len(checked_only_ids)
    updated = len(update_records)

    print(f"[update] checked_only count={checked_not_updated}")
    print(f"[update] full update count={updated}")

    if checked_only_ids:
        print("[update] bulk updating checked_at only")
        for id_chunk in chunked(checked_only_ids, 5000):
            await db.execute(
                update(MillinInvoice)
                .where(MillinInvoice.actual_invoice_id.in_(id_chunk))
                .values(checked_at=now)
            )

    if update_records:
        update_cols = [c for c in valid_cols if c != "actual_invoice_id"]

        record_def_parts = ["actual_invoice_id bigint"] + [
            f"{col} {postgres_cast_for_col(col)}"
            for col in update_cols
        ]
        record_def_sql = ", ".join(record_def_parts)

        set_parts = [f"{col} = src.{col}" for col in update_cols]
        set_parts.append("updated_at = :now")
        set_parts.append("checked_at = :now")
        set_sql = ", ".join(set_parts)

        payload = []
        for row in update_records:
            payload_row = {}
            for key, value in row.items():
                payload_row[key] = json_safe_value(key, value)
            payload.append(payload_row)

        sql = text(f"""
            UPDATE millin_invoices AS m
            SET {set_sql}
            FROM jsonb_to_recordset(CAST(:payload AS jsonb)) AS src({record_def_sql})
            WHERE m.actual_invoice_id = src.actual_invoice_id
        """)

        print(f"[update] bulk full update rows={len(payload)}")
        await db.execute(sql, {"payload": json.dumps(payload), "now": now})

    print("\n[import] committing transaction...")
    await db.commit()
    print("[import] commit complete")

    result = {
        "inserted": inserted,
        "updated": updated,
        "matched_existing": matched_existing,
        "checked_not_updated": checked_not_updated,
        "skipped": skipped,
        "total_rows": original_row_count,
        "invalid_conversion_counts": invalid_counts,
    }

    print(f"[import] result={result}")
    print("==================== END MILLIN IMPORT ====================\n")

    return result