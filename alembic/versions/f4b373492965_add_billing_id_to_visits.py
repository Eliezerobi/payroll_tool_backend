"""add billing_id to visits

Revision ID: f4b373492965
Revises: 627cd660303b
Create Date: 2026-01-06 19:09:58.473838

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4b373492965'
down_revision: Union[str, Sequence[str], None] = '627cd660303b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "visits",
        sa.Column(
            "billing_id",
            sa.BigInteger(),
            sa.ForeignKey("billing_status.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_visits_billing_id", "visits", ["billing_id"])


def downgrade():
    op.drop_index("ix_visits_billing_id", table_name="visits")
    op.drop_column("visits", "billing_id")