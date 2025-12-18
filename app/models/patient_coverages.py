from typing import Optional
from datetime import date, datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Date, Text, TIMESTAMP, func

from app.database import Base


class PatientCoverage(Base):
    __tablename__ = "patient_coverages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # From "Name"
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # From "ID" (external patient ID from the eligibility file)
    external_patient_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # "File Number"
    file_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # "Medical Record ID"
    medical_record_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # "D.O.B."
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    address1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    account_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    patient_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    payer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    policy_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    policy_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now()
    )
