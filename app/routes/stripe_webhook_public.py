from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import os
import json
import requests
import stripe

from app.database import get_db
from app.models import SelfPayCustomer

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_BOARD_ID_STRIPE = os.getenv("MONDAY_BOARD_ID_STRIPE")


def monday_graphql(query: str, variables: dict):
    if not MONDAY_API_KEY:
        raise RuntimeError("Missing MONDAY_API_KEY")

    url = "https://api.monday.com/v2"
    headers = {
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json",
    }

    r = requests.post(
        url,
        headers=headers,
        json={"query": query, "variables": variables},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    if "errors" in data:
        raise RuntimeError(data["errors"])

    return data["data"]


def monday_set_card_on_file(monday_item_id: str, last4: str | None = None):
    if not monday_item_id:
        print("MONDAY SKIP: no monday_item_id")
        return

    if not MONDAY_BOARD_ID_STRIPE:
        raise RuntimeError("Missing MONDAY_BOARD_ID_STRIPE")

    COL_CC_STATUS = "color_mm15yaw2"
    COL_LAST4 = "text_mm152805"

    q = """
    mutation ($board_id: ID!, $item_id: ID!, $column_values: JSON!) {
      change_multiple_column_values(
        board_id: $board_id,
        item_id: $item_id,
        column_values: $column_values
      ) { id }
    }
    """

    colvals = {
        COL_CC_STATUS: {"label": "Card Added"}
    }

    if last4:
        colvals[COL_LAST4] = f"**** {last4}"

    vars_ = {
        "board_id": int(MONDAY_BOARD_ID_STRIPE),
        "item_id": int(monday_item_id),
        "column_values": json.dumps(colvals),
    }

    print("MONDAY UPDATE VARS:", vars_)
    monday_graphql(q, vars_)


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Missing STRIPE_WEBHOOK_SECRET")
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Missing STRIPE_SECRET_KEY")

    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook signature: {str(e)}")

    try:
        print("WEBHOOK EVENT TYPE:", event["type"])

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            print("SESSION OBJECT:", session)

            if session.get("mode") == "setup":
                session_id = session.get("id")
                stripe_customer_id = session.get("customer")
                setup_intent_id = session.get("setup_intent")
                metadata = session.get("metadata") or {}
                monday_item_id = metadata.get("monday_item_id")
                lead_id = metadata.get("lead_id")

                print("SESSION ID:", session_id)
                print("STRIPE CUSTOMER ID:", stripe_customer_id)
                print("SETUP INTENT ID:", setup_intent_id)
                print("LEAD ID:", lead_id)
                print("MONDAY ITEM ID:", monday_item_id)

                payment_method_id = None
                last4 = None

                if setup_intent_id:
                    si = stripe.SetupIntent.retrieve(setup_intent_id)
                    payment_method_id = si.get("payment_method")
                    print("PAYMENT METHOD ID:", payment_method_id)

                    if payment_method_id:
                        pm = stripe.PaymentMethod.retrieve(payment_method_id)
                        if pm and pm.get("card"):
                            last4 = pm["card"].get("last4")
                            print("CARD LAST4:", last4)

                row = None

                if session_id:
                    result = await db.execute(
                        select(SelfPayCustomer).where(
                            SelfPayCustomer.stripe_checkout_session_id == session_id
                        )
                    )
                    row = result.scalar_one_or_none()

                if not row and lead_id:
                    result = await db.execute(
                        select(SelfPayCustomer).where(
                            SelfPayCustomer.lead_id == lead_id
                        )
                    )
                    row = result.scalar_one_or_none()

                if not row and stripe_customer_id:
                    result = await db.execute(
                        select(SelfPayCustomer)
                        .where(SelfPayCustomer.stripe_customer_id == stripe_customer_id)
                        .order_by(SelfPayCustomer.id.desc())
                    )
                    row = result.scalars().first()

                if row:
                    print("DB ROW FOUND:", row.id)

                    row.stripe_setup_intent_id = setup_intent_id
                    row.stripe_payment_method_id = payment_method_id
                    row.cc_status = "Card Added"
                    row.setup_completed = True

                    if not row.monday_item_id and monday_item_id:
                        row.monday_item_id = monday_item_id

                    await db.commit()
                    await db.refresh(row)
                    print("DB COMMIT SUCCESS")
                else:
                    await db.rollback()
                    print(
                        f"DB ROW NOT FOUND for session_id={session_id}, "
                        f"lead_id={lead_id}, stripe_customer_id={stripe_customer_id}"
                    )

                if monday_item_id:
                    try:
                        monday_set_card_on_file(monday_item_id, last4=last4)
                        print("MONDAY UPDATE SUCCESS")
                    except Exception as monday_err:
                        print("MONDAY UPDATE FAILED:", repr(monday_err))
                else:
                    print("MONDAY UPDATE SKIPPED: no monday_item_id in metadata")

        return {"ok": True}

    except Exception as e:
        await db.rollback()
        print("WEBHOOK ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))