"""create millin_invoices table

Revision ID: e39bf1a22018
Revises: da9891099c8c
Create Date: 2026-03-26 01:47:13.738530

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e39bf1a22018'
down_revision: Union[str, Sequence[str], None] = 'da9891099c8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "millin_invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actual_invoice_id", sa.BigInteger(), nullable=True),
        sa.Column("program_type_id", sa.String(), nullable=True),
        sa.Column("file_number", sa.String(), nullable=True),
        sa.Column("patient_id", sa.BigInteger(), nullable=True),
        sa.Column("medical_record_id", sa.BigInteger(), nullable=True),
        sa.Column("patient_full_name", sa.String(), nullable=True),
        sa.Column("claim_identifier", sa.String(), nullable=True),
        sa.Column("transaction_control_number", sa.String(), nullable=True),
        sa.Column("originating_invoice_status", sa.String(), nullable=True),
        sa.Column("final_invoice_status", sa.String(), nullable=True),
        sa.Column("invoice_status_description", sa.String(), nullable=True),
        sa.Column("revenue_code_summary", sa.Text(), nullable=True),
        sa.Column("location_summary", sa.String(), nullable=True),
        sa.Column("provider_summary", sa.String(), nullable=True),
        sa.Column("diagnosis_summary", sa.Text(), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("insurance_payer_id", sa.String(), nullable=True),
        sa.Column("policy_number", sa.String(), nullable=True),
        sa.Column("payer_category_id", sa.String(), nullable=True),
        sa.Column("date_of_service", sa.Date(), nullable=True),
        sa.Column("date_of_service_thru", sa.Date(), nullable=True),
        sa.Column("num_procs", sa.Integer(), nullable=True),
        sa.Column("rate_code", sa.String(), nullable=True),
        sa.Column("procedure_summary", sa.Text(), nullable=True),
        sa.Column("claim_procedure_summary", sa.Text(), nullable=True),
        sa.Column("over_90_day_reason", sa.Text(), nullable=True),
        sa.Column("claim_reason_code_summary", sa.Text(), nullable=True),
        sa.Column("claim_remark_code_summary", sa.Text(), nullable=True),
        sa.Column("charge_summary", sa.Numeric(12, 2), nullable=True),
        sa.Column("payment_summary", sa.Numeric(12, 2), nullable=True),
        sa.Column("adjustment_summary", sa.Numeric(12, 2), nullable=True),
        sa.Column("invoice_balance", sa.Numeric(12, 2), nullable=True),
        sa.Column("av_indicator", sa.String(), nullable=True),
        sa.Column("source_system_identifier", sa.String(), nullable=True),
        sa.Column("issue_tracker_status", sa.String(), nullable=True),
        sa.Column("issue_tracker_category_description", sa.Text(), nullable=True),
        sa.Column("has_note", sa.Boolean(), nullable=True),
        sa.Column("note_color", sa.String(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_millin_invoices_id"), "millin_invoices", ["id"], unique=False)
    op.create_index(op.f("ix_millin_invoices_actual_invoice_id"), "millin_invoices", ["actual_invoice_id"], unique=False)
    op.create_index(op.f("ix_millin_invoices_patient_id"), "millin_invoices", ["patient_id"], unique=False)
    op.create_index(op.f("ix_millin_invoices_claim_identifier"), "millin_invoices", ["claim_identifier"], unique=False)
    op.create_index(op.f("ix_millin_invoices_date_of_service"), "millin_invoices", ["date_of_service"], unique=False)
    op.create_index(op.f("ix_millin_invoices_source_system_identifier"), "millin_invoices", ["source_system_identifier"], unique=False)
    op.create_index(op.f("ix_millin_invoices_checked_at"), "millin_invoices", ["checked_at"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_millin_invoices_checked_at"), table_name="millin_invoices")
    op.drop_index(op.f("ix_millin_invoices_source_system_identifier"), table_name="millin_invoices")
    op.drop_index(op.f("ix_millin_invoices_date_of_service"), table_name="millin_invoices")
    op.drop_index(op.f("ix_millin_invoices_claim_identifier"), table_name="millin_invoices")
    op.drop_index(op.f("ix_millin_invoices_patient_id"), table_name="millin_invoices")
    op.drop_index(op.f("ix_millin_invoices_actual_invoice_id"), table_name="millin_invoices")
    op.drop_index(op.f("ix_millin_invoices_id"), table_name="millin_invoices")
    op.drop_table("millin_invoices")