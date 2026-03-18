"""change invoice_id to string

Revision ID: da9891099c8c
Revises: b6715a1ab6bd
Create Date: 2026-03-12 15:04:17.521956

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'da9891099c8c'
down_revision: Union[str, Sequence[str], None] = 'b6715a1ab6bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # We use postgresql_using to safely cast existing BigInt data to Varchar
    op.alter_column('billing_status', 'invoice_id',
               existing_type=sa.BIGINT(),
               type_=sa.String(length=255),
               postgresql_using='invoice_id::varchar',
               existing_nullable=True)


def downgrade() -> None:
    # To go back, we cast the string back to BigInt
    op.alter_column('billing_status', 'invoice_id',
               existing_type=sa.String(length=255),
               type_=sa.BIGINT(),
               postgresql_using='invoice_id::bigint',
               existing_nullable=True)
