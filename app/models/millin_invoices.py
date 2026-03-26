from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Date,
    Numeric,
    Boolean,
    DateTime,
    func,
)
from app.database import Base


class MillinInvoice(Base):
    __tablename__ = "millin_invoices"

    id = Column(Integer, primary_key=True, index=True)

    actual_invoice_id = Column(BigInteger, unique=True, index=True, nullable=False)

    program_type_id = Column(String, nullable=True)
    file_number = Column(String, nullable=True)
    patient_id = Column(BigInteger, index=True, nullable=True)
    medical_record_id = Column(Text, nullable=True)
    patient_full_name = Column(String, nullable=True)
    claim_identifier = Column(String, index=True, nullable=True)
    transaction_control_number = Column(String, nullable=True)
    originating_invoice_status = Column(String, nullable=True)
    final_invoice_status = Column(String, nullable=True)
    invoice_status_description = Column(String, nullable=True)
    revenue_code_summary = Column(Text, nullable=True)
    location_summary = Column(String, nullable=True)
    provider_summary = Column(String, nullable=True)
    diagnosis_summary = Column(Text, nullable=True)
    invoice_date = Column(Date, nullable=True)
    insurance_payer_id = Column(String, nullable=True)
    policy_number = Column(String, nullable=True)
    payer_category_id = Column(String, nullable=True)
    date_of_service = Column(Date, nullable=True, index=True)
    date_of_service_thru = Column(Date, nullable=True)
    num_procs = Column(Integer, nullable=True)
    rate_code = Column(String, nullable=True)
    procedure_summary = Column(Text, nullable=True)
    claim_procedure_summary = Column(Text, nullable=True)
    over_90_day_reason = Column(Text, nullable=True)
    claim_reason_code_summary = Column(Text, nullable=True)
    claim_remark_code_summary = Column(Text, nullable=True)
    charge_summary = Column(Numeric(12, 2), nullable=True)
    payment_summary = Column(Numeric(12, 2), nullable=True)
    adjustment_summary = Column(Numeric(12, 2), nullable=True)
    invoice_balance = Column(Numeric(12, 2), nullable=True)
    av_indicator = Column(String, nullable=True)
    source_system_identifier = Column(String, nullable=True, index=True)
    issue_tracker_status = Column(String, nullable=True)
    issue_tracker_category_description = Column(Text, nullable=True)
    has_note = Column(Boolean, nullable=True)
    note_color = Column(String, nullable=True)

    checked_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)