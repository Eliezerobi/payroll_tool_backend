"""add note_group_id and note_version to visits

Revision ID: f673778ad2e2
Revises: ab53b39886fa
Create Date: 2025-12-22 17:07:28.825405

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f673778ad2e2'
down_revision: Union[str, Sequence[str], None] = 'ab53b39886fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) Add columns
    op.add_column(
        "visits",
        sa.Column(
            "note_group_id",
            sa.BigInteger(),
            nullable=True,
            comment="FK to billing_status.id (canonical group id for original note + addenda)",
        ),
    )

    op.add_column(
        "visits",
        sa.Column(
            "note_version",
            sa.Integer(),
            nullable=True,
            comment="Version within note_group_id (1=original, 2+=addenda)",
        ),
    )

    # 2) Add FK constraint
    op.create_foreign_key(
        "fk_visits_note_group_id_billing_status",
        "visits",
        "billing_status",
        ["note_group_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3) Index for fast lookups/joins
    op.create_index(
        "ix_visits_note_group_id",
        "visits",
        ["note_group_id"],
    )

    # OPTIONAL (recommended later): backfill rule
    # Leave this out if you're not ready to map groups yet.
    # op.execute("""
    #     UPDATE visits
    #     SET note_version = 1
    #     WHERE note_version IS NULL
    # """)


def downgrade():
    op.drop_index("ix_visits_note_group_id", table_name="visits")

    op.drop_constraint(
        "fk_visits_note_group_id_billing_status",
        "visits",
        type_="foreignkey",
    )

    op.drop_column("visits", "note_version")
    op.drop_column("visits", "note_group_id")