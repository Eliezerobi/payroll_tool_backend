from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.users import User
from app.dependencies.auth import get_current_user

# --- Local imports ---
from app.crud.visits_via_api import fetch_all_hellonote_visits
from app.crud.visits import insert_visit_rows
from app.helloNoteApi.visits_mapper import map_hellonote_list_to_visits
from app.powerAutomate.teamsMessageMyself import notify_teams  # ✅ new import

import os

router = APIRouter()


@router.post("/import-hellonote-visits")
async def import_hellonote_visits(
    dateFrom: str,
    dateTo: str,
    isAllStatus: bool = False,
    isAllStatusWithHold: bool = False,
    isFinalizedDate: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch all HelloNote visits between dateFrom/dateTo, map them to DB structure,
    and insert them using insert_visit_rows().
    """
    stage = "import_hellonote_visits"
    script_name = os.path.basename(__file__)

    try:
        # 1️⃣ Fetch all HelloNote visits into a DataFrame
        df = fetch_all_hellonote_visits(
            date_from=dateFrom,
            date_to=dateTo,
            isAllStatus=isAllStatus,
            isAllStatusWithHold=isAllStatusWithHold,
            isFinalizedDate=isFinalizedDate,
        )
        if df.empty:
            msg = f"No visits found for range {dateFrom}–{dateTo}"
            notify_teams("success", stage, msg, script_name)
            return {"message": msg, "inserted": 0}

        # 2️⃣ Convert DataFrame → list[dict]
        hellonote_items = df.to_dict(orient="records")

        # 3️⃣ Map HelloNote → Visit structure
        mapped_visits = map_hellonote_list_to_visits(hellonote_items)
        for visit in mapped_visits:
            visit["uploaded_by"] = current_user.id
            visit["visit_uid"] = None  # Let insert_visit_rows generate it

        # 4️⃣ Insert visits into database
        result = await insert_visit_rows(db, mapped_visits, uploaded_by=current_user.id)

        msg = (
            f"Imported {result['inserted_count']} visits "
            f"(skipped {result['skipped_notes']}, "
            f"new UIDs {result['visit_uids_created']})"
        )
        print(f"✅ {msg}")
        notify_teams("success", stage, msg, script_name)

        return {
            "message": msg,
            "inserted_count": result["inserted_count"],
            "skipped": result["skipped_notes"],
            "visit_uids_created": result["visit_uids_created"],
        }

    except Exception as e:
        msg = f"Failed during {stage}: {e}"
        print(f"❌ {msg}")
        notify_teams("error", stage, msg, script_name)
        raise HTTPException(status_code=500, detail=msg)
