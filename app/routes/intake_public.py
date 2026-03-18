from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import os
import json
import uuid
import requests
import stripe

from app.database import get_db
from app.models import SelfPayCustomer

router = APIRouter()

# -----------------------
# Env / Config
# -----------------------
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_BOARD_ID_STRIPE = os.getenv("MONDAY_BOARD_ID_STRIPE")
STRIPE_SUCCESS_URL_TMPL = os.getenv("STRIPE_SUCCESS_URL")
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL")


# -----------------------
# Models
# -----------------------
class IntakePayload(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    street: str
    city: str
    state: str
    zip_code: Optional[str] = None
    services: List[str]


# -----------------------
# Monday helpers
# -----------------------
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


def _zip_to_int(zip_code: Optional[str]) -> Optional[int]:
    if not zip_code:
        return None

    digits = "".join(ch for ch in str(zip_code) if ch.isdigit())
    if not digits:
        return None

    digits = digits[:5]

    try:
        return int(digits)
    except Exception:
        return None


def monday_create_item(lead_id: str, payload: IntakePayload) -> str:
    if not MONDAY_BOARD_ID_STRIPE:
        raise RuntimeError("Missing MONDAY_BOARD_ID_STRIPE")

    COL_FIRST = "text_mm151r87"
    COL_LAST = "text_mm153q96"
    COL_EMAIL = "email_mm15sq22"
    COL_PHONE = "phone_mm15pwbs"
    COL_ADDRESS = "text_mm15kq4k"
    COL_STATE = "text_mm15x4t0"
    COL_ZIP = "numeric_mm15vy57"
    COL_DATE_APPLIED = "date4"

    COL_PT = "boolean_mm15er5f"
    COL_OT = "boolean_mm15tqvw"
    COL_ST = "boolean_mm15xrhg"

    COL_CC_STATUS = "color_mm15yaw2"

    item_name = f"{payload.last_name}, {payload.first_name}"
    services_set = {s.strip().upper() for s in (payload.services or [])}

    address_text = f"{payload.street}, {payload.city}, {payload.state}"
    zip_int = _zip_to_int(payload.zip_code)

    today = datetime.now(timezone.utc).date().isoformat()

    column_values = {
        COL_FIRST: payload.first_name,
        COL_LAST: payload.last_name,
        COL_EMAIL: {"email": str(payload.email), "text": str(payload.email)},
        COL_PHONE: {"phone": payload.phone, "text": payload.phone},
        COL_ADDRESS: address_text,
        COL_STATE: payload.state,
        COL_DATE_APPLIED: {"date": today},
        COL_PT: {"checked": "true"} if "PT" in services_set else None,
        COL_OT: {"checked": "true"} if "OT" in services_set else None,
        COL_ST: {"checked": "true"} if "ST" in services_set else None,
        COL_CC_STATUS: {"label": "Waiting On CC"},
    }

    if zip_int is not None:
        column_values[COL_ZIP] = zip_int

    q = """
    mutation ($board_id: ID!, $item_name: String!, $column_values: JSON!) {
      create_item(board_id: $board_id, item_name: $item_name, column_values: $column_values) { id }
    }
    """
    vars_ = {
        "board_id": int(MONDAY_BOARD_ID_STRIPE),
        "item_name": item_name,
        "column_values": json.dumps(column_values),
    }

    data = monday_graphql(q, vars_)
    return data["create_item"]["id"]


# -----------------------
# Public Intake Endpoint
# -----------------------
@router.post("/intake")
async def intake(payload: IntakePayload, db: AsyncSession = Depends(get_db)):
    missing = []
    if not stripe.api_key:
        missing.append("STRIPE_SECRET_KEY")
    if not MONDAY_API_KEY:
        missing.append("MONDAY_API_KEY")
    if not MONDAY_BOARD_ID_STRIPE:
        missing.append("MONDAY_BOARD_ID_STRIPE")
    if not STRIPE_SUCCESS_URL_TMPL:
        missing.append("STRIPE_SUCCESS_URL")
    if not STRIPE_CANCEL_URL:
        missing.append("STRIPE_CANCEL_URL")

    if missing:
        raise HTTPException(status_code=500, detail=f"Missing env vars: {', '.join(missing)}")

    lead_id = str(uuid.uuid4())

    try:
        print("INTAKE HIT")
        print("LEAD ID:", lead_id)

        # 1) Create Monday item
        monday_item_id = monday_create_item(lead_id, payload)
        print("MONDAY ITEM ID:", monday_item_id)

        # 2) Create Stripe customer
        customer = stripe.Customer.create(
            email=str(payload.email),
            name=f"{payload.first_name} {payload.last_name}",
            phone=payload.phone,
            metadata={
                "lead_id": lead_id,
                "monday_item_id": monday_item_id,
            },
        )
        print("STRIPE CUSTOMER ID:", customer.id)

        # 3) Create Stripe Checkout session (setup mode)
        success_url = STRIPE_SUCCESS_URL_TMPL.replace("{LEAD_ID}", lead_id)
        if "{CHECKOUT_SESSION_ID}" not in success_url:
            joiner = "&" if "?" in success_url else "?"
            success_url = success_url + f"{joiner}session_id={{CHECKOUT_SESSION_ID}}"

        session = stripe.checkout.Session.create(
            mode="setup",
            customer=customer.id,
            payment_method_types=["card"],
            client_reference_id=lead_id,
            success_url=success_url,
            cancel_url=STRIPE_CANCEL_URL,
            metadata={
                "lead_id": lead_id,
                "monday_item_id": monday_item_id,
            },
        )
        print("CHECKOUT SESSION ID:", session.id)

        # 4) Save local DB record
        db_row = SelfPayCustomer(
            lead_id=lead_id,
            monday_item_id=monday_item_id,
            stripe_customer_id=customer.id,
            stripe_checkout_session_id=session.id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=str(payload.email),
            phone=payload.phone,
            street=payload.street,
            city=payload.city,
            state=payload.state,
            zip_code=payload.zip_code,
            services=payload.services,
            cc_status="Waiting On CC",
            setup_completed=False,
        )

        db.add(db_row)
        await db.commit()
        await db.refresh(db_row)

        print("DB ROW INSERTED:", db_row.id)

        return {
            "lead_id": lead_id,
            "monday_item_id": monday_item_id,
            "self_pay_customer_id": db_row.id,
            "stripe_customer_id": customer.id,
            "stripe_checkout_session_id": session.id,
            "checkout_url": session.url,
        }

    except Exception as e:
        await db.rollback()
        print("INTAKE ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))