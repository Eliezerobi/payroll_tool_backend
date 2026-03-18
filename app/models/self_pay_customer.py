from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class SelfPayCustomer(Base):
    __tablename__ = "self_pay_customers"

    id = Column(Integer, primary_key=True, index=True)

    lead_id = Column(String, nullable=False, unique=True, index=True)
    monday_item_id = Column(String, nullable=True, index=True)

    stripe_customer_id = Column(String, nullable=False, index=True)
    stripe_checkout_session_id = Column(String, nullable=False, unique=True, index=True)
    stripe_setup_intent_id = Column(String, nullable=True, index=True)
    stripe_payment_method_id = Column(String, nullable=True, index=True)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True)

    street = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

    services = Column(JSONB, nullable=False, server_default="[]")

    cc_status = Column(String, nullable=False, server_default="Waiting On CC")
    setup_completed = Column(Boolean, nullable=False, server_default="false")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())