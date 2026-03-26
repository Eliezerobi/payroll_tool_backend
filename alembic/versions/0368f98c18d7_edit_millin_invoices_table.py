"""edit millin_invoices table

Revision ID: 0368f98c18d7
Revises: e39bf1a22018
Create Date: 2026-03-26 01:57:00.183854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0368f98c18d7'
down_revision: Union[str, Sequence[str], None] = 'e39bf1a22018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "millin_invoices",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "millin_invoices",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.alter_column(
        "millin_invoices",
        "actual_invoice_id",
        existing_type=sa.BIGINT(),
        nullable=False,
    )

    op.drop_index("ix_millin_invoices_actual_invoice_id", table_name="millin_invoices")
    op.create_index(
        "ix_millin_invoices_actual_invoice_id",
        "millin_invoices",
        ["actual_invoice_id"],
        unique=True,
    )

    op.drop_column("millin_invoices", "uploaded_at")



def downgrade() -> None:
    op.add_column(
        "millin_invoices",
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.drop_index("ix_millin_invoices_actual_invoice_id", table_name="millin_invoices")
    op.create_index(
        "ix_millin_invoices_actual_invoice_id",
        "millin_invoices",
        ["actual_invoice_id"],
        unique=False,
    )

    op.alter_column(
        "millin_invoices",
        "actual_invoice_id",
        existing_type=sa.BIGINT(),
        nullable=True,
    )

    op.drop_column("millin_invoices", "updated_at")
    op.drop_column("millin_invoices", "created_at")