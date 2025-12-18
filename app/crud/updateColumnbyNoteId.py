# app/crud/update_visits_from_xlsx_same_folder.py

import os
import re
from typing import Any, Optional, List, Tuple

import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv


# -----------------------------------------------------------
# Load .env from project root
# -----------------------------------------------------------
CRUD_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CRUD_DIR, "..", ".."))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(ENV_PATH)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "payroll_tool")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")

BATCH_SIZE = 5000

# -----------------------------------------------------------
# SAFETY: only allow updating these visits columns
# -----------------------------------------------------------
ALLOWED_VISITS_COLUMNS = {
    "hold",
    "hold_reason",
    "status",
    "uploaded_to_monday",
    "printed_note_filename",
    "non_duplicate_confirmation",
    "rendering_provider_npi",
}

# -----------------------------------------------------------
# File location (same folder as this CRUD file)
# Change filename if you want a different default.
# -----------------------------------------------------------
DEFAULT_XLSX_FILENAME = "5072970.xlsx"


# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_")


def to_none_if_blank(x: Any) -> Any:
    if x is None:
        return None
    if isinstance(x, float) and np.isnan(x):
        return None
    s = str(x).strip()
    if s.lower() in {"", "nan", "nat", "none", "null"}:
        return None
    return x


def coerce_note_id(x: Any) -> Optional[int]:
    x = to_none_if_blank(x)
    if x is None:
        return None
    try:
        if isinstance(x, float) and x.is_integer():
            return int(x)
        return int(str(x).strip())
    except Exception:
        return None


def resolve_column(df: pd.DataFrame, desired: str) -> str:
    desired_n = _norm(desired)
    mapping = {_norm(c): c for c in df.columns}
    if desired_n not in mapping:
        raise ValueError(
            f'Column "{desired}" not found in file. Available: {list(df.columns)}'
        )
    return mapping[desired_n]


def resolve_note_id_column(df: pd.DataFrame) -> str:
    candidates = ["note_id", "noteid", "note id", "NOTE ID", "NOTE_ID", "noteId", "hn_note_id"]
    mapping = {_norm(c): c for c in df.columns}
    for cand in candidates:
        k = _norm(cand)
        if k in mapping:
            return mapping[k]
    raise ValueError(
        "Could not find NOTE ID column in file. "
        "Expected something like NOTE ID / note_id / noteId / hn_note_id."
    )


# -----------------------------------------------------------
# Main function you will call
# -----------------------------------------------------------
def update_visits_from_xlsx_same_folder(column_name: str, filename: str = DEFAULT_XLSX_FILENAME) -> dict:
    """
    Reads an XLSX file from the SAME folder as this CRUD file and updates visits.<column_name>
    matched by visits.note_id.

    The XLSX must contain:
      - NOTE ID column (any common variant)
      - a column whose header matches `column_name` (case/spacing insensitive)

    Returns a summary dict.
    """
    if column_name not in ALLOWED_VISITS_COLUMNS:
        raise ValueError(
            f'Column "{column_name}" is not allowed. Add it to ALLOWED_VISITS_COLUMNS if intended.'
        )

    filepath = os.path.join(CRUD_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"XLSX file not found at: {filepath}")

    df = pd.read_excel(filepath)
    if df.empty:
        return {"updated": 0, "missing_estimated": 0, "file": filepath}

    note_col = resolve_note_id_column(df)
    value_col = resolve_column(df, column_name)

    pairs: List[Tuple[int, Any]] = []
    for _, row in df.iterrows():
        note_id = coerce_note_id(row.get(note_col))
        if note_id is None:
            continue
        value = to_none_if_blank(row.get(value_col))
        pairs.append((note_id, value))

    if not pairs:
        return {"updated": 0, "missing_estimated": 0, "file": filepath}

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
    )
    cur = conn.cursor()

    updated_total = 0

    sql = f"""
        UPDATE visits AS v
        SET {column_name} = d.value
        FROM (VALUES %s) AS d(note_id, value)
        WHERE v.note_id = d.note_id
    """

    for i in range(0, len(pairs), BATCH_SIZE):
        batch = pairs[i : i + BATCH_SIZE]
        execute_values(cur, sql, batch, template="(%s, %s)")
        updated_total += cur.rowcount

    conn.commit()
    conn.close()

    missing_est = max(0, len(pairs) - updated_total)

    return {
        "updated": updated_total,
        "missing_estimated": missing_est,
        "rows_in_file_with_note_id": len(pairs),
        "file": filepath,
        "target_column": column_name,
        "note_id_column_in_file": note_col,
        "value_column_in_file": value_col,
    }


# -----------------------------------------------------------
# __main__ entrypoint (NO CLI, fixed behavior)
# -----------------------------------------------------------
if __name__ == "__main__":
    """
    Direct execution mode:
    - Reads visits_update.xlsx from this folder
    - Updates the specified visits column by note_id
    """

    # 🔧 CHANGE THIS to the column you want to update
    TARGET_COLUMN = "rendering_provider_npi"
    # Example alternatives:
    # TARGET_COLUMN = "hold"
    # TARGET_COLUMN = "status"
    # TARGET_COLUMN = "printed_note_filename"

    try:
        result = update_visits_from_xlsx_same_folder(TARGET_COLUMN)
        print("✅ Update completed")
        print(result)
    except Exception as e:
        print("❌ Update failed")
        raise
