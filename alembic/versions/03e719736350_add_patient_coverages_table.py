"""add patient_coverages table

Revision ID: 03e719736350
Revises: fe0e22685066
Create Date: 2025-12-11 04:22:09.824261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03e719736350'
down_revision: Union[str, Sequence[str], None] = 'fe0e22685066'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patient_coverages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("external_patient_id", sa.String(50), nullable=True),
        sa.Column("file_number", sa.String(50), nullable=True),
        sa.Column("medical_record_id", sa.String(50), nullable=True),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("address1", sa.String(255), nullable=True),
        sa.Column("address2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(20), nullable=True),
        sa.Column("zip", sa.String(20), nullable=True),
        sa.Column("account_status", sa.String(50), nullable=True),
        sa.Column("patient_type", sa.String(50), nullable=True),
        sa.Column("payer", sa.String(255), nullable=True),
        sa.Column("policy_type", sa.String(50), nullable=True),
        sa.Column("policy_number", sa.String(100), nullable=True),

        sa.Column("created_at", sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_patient_coverages_external_patient_id",
        "patient_coverages",
        ["external_patient_id"],
    )
    op.create_index(
        "ix_patient_coverages_medical_record_id",
        "patient_coverages",
        ["medical_record_id"],
    )
    op.create_index(
        "ix_patient_coverages_policy_number",
        "patient_coverages",
        ["policy_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_patient_coverages_policy_number", table_name="patient_coverages")
    op.drop_index("ix_patient_coverages_medical_record_id", table_name="patient_coverages")
    op.drop_index("ix_patient_coverages_external_patient_id", table_name="patient_coverages")
    op.drop_table("patient_coverages")