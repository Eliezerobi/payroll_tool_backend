from typing import Optional
from datetime import datetime, date
from sqlalchemy import Numeric
from decimal import Decimal


from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    Integer, String, Date, Boolean, Text, BigInteger, TIMESTAMP,
    func, ForeignKey
)

from app.database import Base


class BillingStatus(Base):
    __tablename__ = "billing_status"

    # Canonical group ID (int) for "this logical visit/note", stable across addenda
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        index=True)

    # Current lifecycle status (keep as string to start; you can convert to Enum later)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="new",
        index=True,
        comment="Current billing lifecycle status (e.g., new, ready, billed, paid, denied, hold, needs_rebill_review)"
    )

    # Optional: if you want to track primary vs secondary separately, you can add more columns later.
    billed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    paid_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    paid_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Paid amount in dollars"
    )


    check_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Payer check/EFT reference number associated with payment"
    )
    hold: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Operational hold flag (billing workflow hold)"
    )

    hold_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Version pointers (critical for your addendum/version control plan)
    current_note_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("visits.note_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Points to visits.note_id representing the latest version in this group"
    )

    billed_note_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("visits.note_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Points to visits.note_id representing the version that was actually billed"
    )

    # Invoice / batch linkage (optional now; add FK once invoices table exists)
    invoice_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
        comment="Optional link to invoice/batch id if you implement invoices"
    )

    review_needed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="If true, requires manual review before billing/rebilling"
    )
    review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
