"""change medical_record_id to text on millin_invoices

Revision ID: d1bffb09f6a6
Revises: 0368f98c18d7
Create Date: 2026-03-26 16:03:33.829583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1bffb09f6a6'
down_revision: Union[str, Sequence[str], None] = '0368f98c18d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "millin_invoices",
        "medical_record_id",
        existing_type=sa.BigInteger(),
        type_=sa.Text(),
        existing_nullable=True,
        postgresql_using="medical_record_id::text",
    )


def downgrade() -> None:
    op.alter_column(
        "millin_invoices",
        "medical_record_id",
        existing_type=sa.Text(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using="""
            CASE
                WHEN medical_record_id ~ '^[0-9]+$'
                THEN medical_record_id::bigint
                ELSE NULL
            END
        """,
    )