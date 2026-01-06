"""Widen visits varchar columns for import

Revision ID: 56d7b319f72f
Revises: f673778ad2e2
Create Date: 2026-01-05 18:16:27.558642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56d7b319f72f'
down_revision: Union[str, Sequence[str], None] = 'f673778ad2e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # visits.attendance: varchar(50) -> varchar(255)
    op.alter_column(
        "visits",
        "attendance",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.VARCHAR(length=255),
        existing_nullable=True,
    )

    # visits.auth_number: varchar(50) -> varchar(255)
    op.alter_column(
        "visits",
        "auth_number",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.VARCHAR(length=255),
        existing_nullable=True,
    )

    # visits.medical_record_no: varchar(50) -> varchar(255)
    op.alter_column(
        "visits",
        "medical_record_no",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.VARCHAR(length=255),
        existing_nullable=True,
    )

    # visits.primary_ins_id: varchar(50) -> varchar(150)
    op.alter_column(
        "visits",
        "primary_ins_id",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.VARCHAR(length=150),
        existing_nullable=True,
    )

    # visits.secondary_ins_id: varchar(50) -> varchar(150)
    op.alter_column(
        "visits",
        "secondary_ins_id",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.VARCHAR(length=150),
        existing_nullable=True,
    )

    # visits.cpt_code: varchar(50) -> varchar(150)
    op.alter_column(
        "visits",
        "cpt_code",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.VARCHAR(length=150),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Revert in reverse order

    op.alter_column(
        "visits",
        "cpt_code",
        existing_type=sa.VARCHAR(length=150),
        type_=sa.VARCHAR(length=50),
        existing_nullable=True,
    )

    op.alter_column(
        "visits",
        "secondary_ins_id",
        existing_type=sa.VARCHAR(length=150),
        type_=sa.VARCHAR(length=50),
        existing_nullable=True,
    )

    op.alter_column(
        "visits",
        "primary_ins_id",
        existing_type=sa.VARCHAR(length=150),
        type_=sa.VARCHAR(length=50),
        existing_nullable=True,
    )

    op.alter_column(
        "visits",
        "medical_record_no",
        existing_type=sa.VARCHAR(length=255),
        type_=sa.VARCHAR(length=50),
        existing_nullable=True,
    )

    op.alter_column(
        "visits",
        "auth_number",
        existing_type=sa.VARCHAR(length=255),
        type_=sa.VARCHAR(length=50),
        existing_nullable=True,
    )

    op.alter_column(
        "visits",
        "attendance",
        existing_type=sa.VARCHAR(length=255),
        type_=sa.VARCHAR(length=50),
        existing_nullable=True,
    )
