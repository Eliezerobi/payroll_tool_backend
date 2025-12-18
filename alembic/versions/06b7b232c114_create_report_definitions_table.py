"""create report_definitions table

Revision ID: 06b7b232c114
Revises: ce772857c0c7
Create Date: 2025-11-10 04:16:15.907787

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06b7b232c114'
down_revision: Union[str, Sequence[str], None] = 'ce772857c0c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'report_definitions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('frequency', sa.String(50), nullable=False, server_default='daily'),
        sa.Column('sql_file', sa.String(255), nullable=False),
        sa.Column('output_table', sa.String(255), nullable=False),
        sa.Column('output_columns', sa.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )



def downgrade():
    op.drop_table('report_definitions')