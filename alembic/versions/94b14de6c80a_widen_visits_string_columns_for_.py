"""Widen visits string columns for HelloNote import

Revision ID: 94b14de6c80a
Revises: 56d7b319f72f
Create Date: 2026-01-05 18:18:05.991224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94b14de6c80a'
down_revision: Union[str, Sequence[str], None] = '56d7b319f72f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # attendance: varchar(50) -> varchar(255)
    op.alter_column(
        "visits",
        "attendance",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.VARCHAR(length=255),
        existing_nullable=True,
    )

    # auth_number: varchar(50) -> varchar(255)
    op.alter_column(
        "visits",
        "auth_number",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.VARCHAR(length=255),
        existing_nullable=True,
    )

    # cpt_code: varchar(50) -> varchar(150)
    op.alter_column(
        "visits",
        "cpt_code",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.VARCHAR(length=150),
        existing_nullable=True,
    )

    # medical_record_no: varchar(50) -> varchar(255)
    op.alter_column(
        "visits",
        "medical_record_no",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.VARCHAR(length=255),
        existing_nullable=True,
    )

    # primary_ins_id: varchar(50) -> varchar(150)
    op.alter_column(
        "visits",
        "primary_ins_id",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.VARCHAR(length=150),
        existing_nullable=True,
    )

    # secondary_ins_id: varchar(50) -> varchar(255)
    op.alter_column(
        "visits",
        "secondary_ins_id",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.VARCHAR(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    # revert back to varchar(50) for all affected columns

    op.alter_column(
        "visits",
        "secondary_ins_id",
        existing_type=sa.VARCHAR(length=255),
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
        "cpt_code",
        existing_type=sa.VARCHAR(length=150),
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