"""change billing_status.paid_amount to numeric

Revision ID: 627cd660303b
Revises: 94b14de6c80a
Create Date: 2026-01-06 19:04:41.460927

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '627cd660303b'
down_revision: Union[str, Sequence[str], None] = '94b14de6c80a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1️⃣ Convert paid_amount from VARCHAR → NUMERIC
    op.execute("""
        ALTER TABLE billing_status
        ALTER COLUMN paid_amount
        TYPE NUMERIC(12,2)
        USING NULLIF(paid_amount, '')::numeric;
    """)

    # 2️⃣ Add check_number column
    op.add_column(
        "billing_status",
        sa.Column(
            "check_number",
            sa.String(length=100),
            nullable=True
        )
    )

    # 3️⃣ Index for reconciliation lookups
    op.create_index(
        "ix_billing_status_check_number",
        "billing_status",
        ["check_number"]
    )


def downgrade():
    # Reverse index + column
    op.drop_index("ix_billing_status_check_number", table_name="billing_status")
    op.drop_column("billing_status", "check_number")

    # Revert paid_amount back to VARCHAR
    op.execute("""
        ALTER TABLE billing_status
        ALTER COLUMN paid_amount
        TYPE VARCHAR(50)
        USING paid_amount::text;
    """)