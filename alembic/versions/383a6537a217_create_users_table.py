"""create users table

Revision ID: 383a6537a217
Revises: c55ec56baf20
Create Date: 2025-08-28 18:30:22.498967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '383a6537a217'
down_revision: Union[str, Sequence[str], None] = 'c55ec56baf20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create users table."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("username", sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Downgrade schema: drop users table."""
    op.drop_table("users")
