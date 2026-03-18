from datetime import datetime, timezone
import os

import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import SelfPayCustomer, SelfPayCharge
from app.schemas.stripe import ChargeClientVisitRequest

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


async def _get_customer_or_404(db: AsyncSession, client_id: int) -> SelfPayCustomer:
    result = await db.execute(
        select(SelfPayCustomer).where(SelfPayCustomer.id == client_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Client not found")

    if not customer.setup_completed:
        raise HTTPException(status_code=400, detail="Card setup not completed")

    if not customer.stripe_customer_id or not customer.stripe_payment_method_id:
        raise HTTPException(
            status_code=400,
            detail="Missing Stripe customer/payment method",
        )

    return customer


async def _ensure_not_already_charged(
    db: AsyncSession,
    client_id: int,
    visit_id: str,
) -> None:
    result = await db.execute(
        select(SelfPayCharge).where(
            SelfPayCharge.client_id == client_id,
            SelfPayCharge.visit_id == visit_id,
            SelfPayCharge.status == "succeeded",
        )
    )
    existing_success = result.scalar_one_or_none()

    if existing_success:
        raise HTTPException(
            status_code=400,
            detail="This visit was already successfully charged",
        )


def _get_payment_method_card_details(payment_method_id: str) -> tuple[str | None, str | None]:
    try:
        pm = stripe.PaymentMethod.retrieve(payment_method_id)
        card = getattr(pm, "card", None)
        if not card:
            return None, None
        return getattr(card, "brand", None), getattr(card, "last4", None)
    except Exception:
        return None, None


def _extract_stripe_error_details(e: Exception) -> dict:
    detail = {
        "message": str(e),
        "code": None,
        "decline_code": None,
        "payment_intent_id": None,
        "payment_intent_status": None,
    }

    stripe_error_obj = getattr(e, "error", None)
    if stripe_error_obj:
        detail["message"] = getattr(stripe_error_obj, "message", None) or detail["message"]
        detail["code"] = getattr(stripe_error_obj, "code", None)
        detail["decline_code"] = getattr(stripe_error_obj, "decline_code", None)

        payment_intent = getattr(stripe_error_obj, "payment_intent", None)
        if payment_intent:
            detail["payment_intent_id"] = getattr(payment_intent, "id", None)
            detail["payment_intent_status"] = getattr(payment_intent, "status", None)
            return detail

    json_body = getattr(e, "json_body", None) or {}
    err = json_body.get("error", {}) if isinstance(json_body, dict) else {}
    payment_intent = err.get("payment_intent") or {}

    detail["message"] = err.get("message") or detail["message"]
    detail["code"] = err.get("code") or detail["code"]
    detail["decline_code"] = err.get("decline_code") or detail["decline_code"]
    detail["payment_intent_id"] = payment_intent.get("id") or detail["payment_intent_id"]
    detail["payment_intent_status"] = (
        payment_intent.get("status") or detail["payment_intent_status"]
    )

    return detail


async def _save_charge_row(db: AsyncSession, charge_row: SelfPayCharge) -> SelfPayCharge:
    try:
        db.add(charge_row)
        await db.commit()
        await db.refresh(charge_row)
        return charge_row
    except Exception:
        await db.rollback()
        raise


@router.post("/self-pay/charge-client-visit")
async def charge_client_visit(
    req: ChargeClientVisitRequest,
    db: AsyncSession = Depends(get_db),
):
    customer = await _get_customer_or_404(db, req.client_id)
    await _ensure_not_already_charged(db, req.client_id, req.visit_id)

    card_brand, card_last4 = _get_payment_method_card_details(
        customer.stripe_payment_method_id
    )

    idempotency_key = f"selfpay-client-{customer.id}-visit-{req.visit_id}"

    try:
        pi = stripe.PaymentIntent.create(
            amount=req.amount_cents,
            currency="usd",
            customer=customer.stripe_customer_id,
            payment_method=customer.stripe_payment_method_id,
            confirm=True,
            off_session=True,
            description=f"Self-pay visit charge for {customer.first_name} {customer.last_name}",
            metadata={
                "client_id": str(customer.id),
                "visit_id": str(req.visit_id),
                "visit_number": str(req.visit_number or ""),
                "lead_id": str(customer.lead_id),
            },
            idempotency_key=idempotency_key,
        )

        charge_row = SelfPayCharge(
            client_id=customer.id,
            visit_id=req.visit_id,
            visit_number=req.visit_number,
            amount_cents=req.amount_cents,
            stripe_customer_id=customer.stripe_customer_id,
            stripe_payment_method_id=customer.stripe_payment_method_id,
            stripe_payment_intent_id=pi.id,
            card_brand=card_brand,
            card_last4=card_last4,
            status=pi.status,
            failure_code=None,
            failure_message=None,
            charged_at=datetime.now(timezone.utc) if pi.status == "succeeded" else None,
        )

        charge_row = await _save_charge_row(db, charge_row)

        return {
            "ok": True,
            "charge_id": charge_row.id,
            "payment_intent_id": pi.id,
            "status": pi.status,
            "amount_cents": pi.amount,
            "card_last4": charge_row.card_last4,
            "card_brand": charge_row.card_brand,
        }

    except stripe.CardError as e:
        err = _extract_stripe_error_details(e)

        charge_row = SelfPayCharge(
            client_id=customer.id,
            visit_id=req.visit_id,
            visit_number=req.visit_number,
            amount_cents=req.amount_cents,
            stripe_customer_id=customer.stripe_customer_id,
            stripe_payment_method_id=customer.stripe_payment_method_id,
            stripe_payment_intent_id=err["payment_intent_id"],
            card_brand=card_brand,
            card_last4=card_last4,
            status=err["payment_intent_status"] or "failed",
            failure_code=err["code"],
            failure_message=err["message"],
            charged_at=None,
        )

        charge_row = await _save_charge_row(db, charge_row)

        raise HTTPException(
            status_code=402,
            detail={
                "ok": False,
                "charge_id": charge_row.id,
                "message": err["message"],
                "code": err["code"],
                "decline_code": err["decline_code"],
                "status": charge_row.status,
            },
        )

    except stripe.StripeError as e:
        err = _extract_stripe_error_details(e)

        charge_row = SelfPayCharge(
            client_id=customer.id,
            visit_id=req.visit_id,
            visit_number=req.visit_number,
            amount_cents=req.amount_cents,
            stripe_customer_id=customer.stripe_customer_id,
            stripe_payment_method_id=customer.stripe_payment_method_id,
            stripe_payment_intent_id=err["payment_intent_id"],
            card_brand=card_brand,
            card_last4=card_last4,
            status=err["payment_intent_status"] or "failed",
            failure_code=err["code"] or "stripe_error",
            failure_message=err["message"],
            charged_at=None,
        )

        charge_row = await _save_charge_row(db, charge_row)

        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "charge_id": charge_row.id,
                "message": err["message"],
                "code": err["code"],
                "status": charge_row.status,
            },
        )