"""make billing_status.id auto increment

Revision ID: 8a28a13915db
Revises: f4b373492965
Create Date: 2026-01-06 19:20:55.157991

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a28a13915db'
down_revision: Union[str, Sequence[str], None] = 'f4b373492965'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # billing_status.id already auto-increments via nextval('billing_status_id_seq')
    pass


def downgrade():
    pass