from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patients import Patient


REQUIRED_COLUMNS = {"patient_id", "Deductible", "QMB"}


async def import_met_deductible_from_excel_bytes(
    db: AsyncSession,
    excel_bytes: bytes,
) -> Dict[str, Any]:
    """
    Excel columns required:
      - patient_id
      - Deductible
      - QMB

    Rule:
      If QMB == 0 and Deductible == 0 => set patients.met_deductible = true

    Behavior:
      - Only sets True (does NOT set False for anyone)
      - Ignores rows missing/invalid patient_id
    """
    df = pd.read_excel(BytesIO(excel_bytes))
    df.columns = [str(c).strip() for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df["patient_id"] = pd.to_numeric(df["patient_id"], errors="coerce")
    df["Deductible"] = pd.to_numeric(df["Deductible"], errors="coerce")
    df["QMB"] = pd.to_numeric(df["QMB"], errors="coerce")

    eligible_ids: List[int] = (
        df[
            df["patient_id"].notna()
            & (df["QMB"] == 0)
            & (df["Deductible"] == 0)
        ]["patient_id"]
        .astype("int64")
        .drop_duplicates()
        .tolist()
    )

    if not eligible_ids:
        return {"eligible_patient_ids": 0, "updated": 0}

    stmt = (
        update(Patient)
        .where(Patient.id.in_(eligible_ids))
        .values(met_deductible=True)
    )

    result = await db.execute(stmt)
    await db.commit()

    updated = int(getattr(result, "rowcount", 0) or 0)

    return {
        "eligible_patient_ids": len(eligible_ids),
        "updated": updated,
    }
