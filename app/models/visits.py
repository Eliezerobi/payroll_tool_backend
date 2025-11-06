from typing import Optional
from datetime import datetime, date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Date, Boolean, Text, BigInteger, TIMESTAMP, func, ForeignKey, UUID
from app.database import Base

class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    visit_uid: Mapped[str] = mapped_column(String(20), nullable=True, index=True, comment="Stable visit identifier across related notes (not unique, reused)")
    note_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True)
    patient_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    note: Mapped[Optional[str]] = mapped_column(String(255))
    note_number: Mapped[int] = mapped_column(Integer)
    case_description: Mapped[Optional[str]] = mapped_column(String(255))
    case_date: Mapped[Optional[Date]] = mapped_column(Date)
    primary_ins_id: Mapped[Optional[str]] = mapped_column(String(50))
    primary_insurance: Mapped[Optional[str]] = mapped_column(String(100))
    secondary_ins_id: Mapped[Optional[str]] = mapped_column(String(50))
    secondary_insurance: Mapped[Optional[str]] = mapped_column(String(100))
    note_date: Mapped[Optional[Date]] = mapped_column(Date)
    referring_provider: Mapped[Optional[str]] = mapped_column(String(150))
    ref_provider_npi: Mapped[Optional[str]] = mapped_column(String(20))
    diagnosis: Mapped[Optional[str]] = mapped_column(Text)
    finalized_date: Mapped[Optional[Date]] = mapped_column(Date)
    pos: Mapped[Optional[str]] = mapped_column(String(20))
    visit_type: Mapped[Optional[str]] = mapped_column(String(100))
    attendance: Mapped[Optional[str]] = mapped_column(String(50))
    comments: Mapped[Optional[str]] = mapped_column(Text)
    supervising_therapist: Mapped[Optional[str]] = mapped_column(String(150))
    visiting_therapist: Mapped[Optional[str]] = mapped_column(String(150))
    cpt_code: Mapped[Optional[str]] = mapped_column(String(50))
    total_units: Mapped[Optional[int]] = mapped_column(Integer)
    date_billed: Mapped[Optional[Date]] = mapped_column(Date)
    billed_comment: Mapped[Optional[str]] = mapped_column(Text)
    date_of_birth: Mapped[Optional[Date]] = mapped_column(Date)
    patient_street1: Mapped[Optional[str]] = mapped_column(String(255))
    patient_street2: Mapped[Optional[str]] = mapped_column(String(255))
    patient_city: Mapped[Optional[str]] = mapped_column(String(100))
    patient_state: Mapped[Optional[str]] = mapped_column(String(50))
    patient_zip: Mapped[Optional[str]] = mapped_column(String(20))
    case_type: Mapped[Optional[str]] = mapped_column(String(100))
    location: Mapped[Optional[str]] = mapped_column(String(100))
    hold: Mapped[bool] = mapped_column(Boolean, default=False)
    billed: Mapped[bool] = mapped_column(Boolean, default=False)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_number: Mapped[Optional[str]] = mapped_column(String(50))
    medical_record_no: Mapped[Optional[str]] = mapped_column(String(50))
    medical_diagnosis: Mapped[Optional[str]] = mapped_column(Text)
    rendering_provider_npi: Mapped[Optional[str]] = mapped_column(String(20))
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    uploaded_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    review_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    review_reason: Mapped[Optional[str]] = mapped_column(Text)
    case_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    time_in: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    time_out: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    review_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),  # 👈 enforce FK to users table
        nullable=True
    )