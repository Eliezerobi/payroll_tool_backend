"""split address, add case_id, time_in, time_out

Revision ID: ce772857c0c7
Revises: 7b904fbd8529
Create Date: 2025-11-04 17:33:10.918079

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce772857c0c7'
down_revision: Union[str, Sequence[str], None] = '7b904fbd8529'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new address, case, and time columns
    op.add_column("visits", sa.Column("case_id", sa.BigInteger(), nullable=True))
    op.add_column("visits", sa.Column("patient_street1", sa.String(length=255), nullable=True))
    op.add_column("visits", sa.Column("patient_street2", sa.String(length=255), nullable=True))
    op.add_column("visits", sa.Column("patient_city", sa.String(length=100), nullable=True))
    op.add_column("visits", sa.Column("patient_state", sa.String(length=50), nullable=True))
    op.add_column("visits", sa.Column("patient_zip", sa.String(length=20), nullable=True))
    op.add_column("visits", sa.Column("time_in", sa.TIMESTAMP(), nullable=True))
    op.add_column("visits", sa.Column("time_out", sa.TIMESTAMP(), nullable=True))

    # Drop the old single address column
    op.drop_column("visits", "address")


def downgrade() -> None:
    # Recreate the old address column
    op.add_column("visits", sa.Column("address", sa.Text(), nullable=True))

    # Drop new columns
    op.drop_column("visits", "time_out")
    op.drop_column("visits", "time_in")
    op.drop_column("visits", "patient_zip")
    op.drop_column("visits", "patient_state")
    op.drop_column("visits", "patient_city")
    op.drop_column("visits", "patient_street2")
    op.drop_column("visits", "patient_street1")
    op.drop_column("visits", "case_id")