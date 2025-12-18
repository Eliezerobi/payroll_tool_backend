"""Add exclude_chha to report_definitions

Revision ID: fe0e22685066
Revises: 06b7b232c114
Create Date: 2025-11-24 03:29:24.394439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe0e22685066'
down_revision: Union[str, Sequence[str], None] = '06b7b232c114'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. Add column with temporary NULL allowed (safe for large tables)
    op.add_column(
        "report_definitions",
        sa.Column("exclude_chha", sa.Boolean(), nullable=True)
    )

    # 2. Set default value for existing rows
    op.execute("UPDATE report_definitions SET exclude_chha = true")

    # 3. Alter column to NOT NULL with default
    op.alter_column(
        "report_definitions",
        "exclude_chha",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )


def downgrade():
    op.drop_column("report_definitions", "exclude_chha")
