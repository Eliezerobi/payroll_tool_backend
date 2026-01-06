"""create billing_status table

Revision ID: ab53b39886fa
Revises: 03e719736350
Create Date: 2025-12-22 17:04:00.647744

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab53b39886fa'
down_revision: Union[str, Sequence[str], None] = '03e719736350'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "billing_status",
        sa.Column("id", sa.BigInteger(), primary_key=True, nullable=False),

        sa.Column("status", sa.String(length=50), nullable=False, server_default="new"),

        sa.Column("billed_date", sa.Date(), nullable=True),
        sa.Column("paid_date", sa.Date(), nullable=True),

        sa.Column("paid_amount", sa.String(length=50), nullable=True),

        sa.Column("hold", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("hold_reason", sa.Text(), nullable=True),

        sa.Column(
            "current_note_id",
            sa.BigInteger(),
            sa.ForeignKey("visits.note_id", ondelete="SET NULL"),
            nullable=True
        ),
        sa.Column(
            "billed_note_id",
            sa.BigInteger(),
            sa.ForeignKey("visits.note_id", ondelete="SET NULL"),
            nullable=True
        ),

        sa.Column("invoice_id", sa.BigInteger(), nullable=True),

        sa.Column("review_needed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("review_reason", sa.Text(), nullable=True),

        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_billing_status_id", "billing_status", ["id"])
    op.create_index("ix_billing_status_status", "billing_status", ["status"])
    op.create_index("ix_billing_status_current_note_id", "billing_status", ["current_note_id"])
    op.create_index("ix_billing_status_billed_note_id", "billing_status", ["billed_note_id"])
    op.create_index("ix_billing_status_invoice_id", "billing_status", ["invoice_id"])


def downgrade():
    op.drop_index("ix_billing_status_invoice_id", table_name="billing_status")
    op.drop_index("ix_billing_status_billed_note_id", table_name="billing_status")
    op.drop_index("ix_billing_status_current_note_id", table_name="billing_status")
    op.drop_index("ix_billing_status_status", table_name="billing_status")
    op.drop_index("ix_billing_status_id", table_name="billing_status")
    op.drop_table("billing_status")