from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class SelfPayCharge(Base):
    __tablename__ = "self_pay_charges"

    id = Column(Integer, primary_key=True, index=True)

    client_id = Column(Integer, nullable=False, index=True)
    visit_id = Column(String, nullable=False, index=True)
    visit_number = Column(Integer, nullable=True)

    amount_cents = Column(Integer, nullable=False)

    stripe_customer_id = Column(String, nullable=True)
    stripe_payment_method_id = Column(String, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True, index=True)

    card_brand = Column(String, nullable=True)
    card_last4 = Column(String(4), nullable=True)

    status = Column(String, nullable=False, index=True)  # succeeded / failed / requires_action / etc.
    failure_code = Column(String, nullable=True)
    failure_message = Column(Text, nullable=True)

    charged_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)