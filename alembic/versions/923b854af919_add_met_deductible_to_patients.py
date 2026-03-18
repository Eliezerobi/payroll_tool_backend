"""add met_deductible to patients

Revision ID: 923b854af919
Revises: 8a28a13915db
Create Date: 2026-02-02 21:46:54.742125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '923b854af919'
down_revision: Union[str, Sequence[str], None] = '8a28a13915db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "patients",
        sa.Column(
            "met_deductible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade():
    op.drop_column("patients", "met_deductible")