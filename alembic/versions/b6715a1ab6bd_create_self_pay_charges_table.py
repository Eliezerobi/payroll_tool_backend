"""create self_pay_charges table

Revision ID: b6715a1ab6bd
Revises: 0a80c1897113
Create Date: 2026-03-10 02:58:06.647144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6715a1ab6bd'
down_revision: Union[str, Sequence[str], None] = '0a80c1897113'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "self_pay_charges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("visit_id", sa.String(), nullable=False),
        sa.Column("visit_number", sa.Integer(), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),

        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("stripe_payment_method_id", sa.String(), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(), nullable=True),

        sa.Column("card_brand", sa.String(), nullable=True),
        sa.Column("card_last4", sa.String(length=4), nullable=True),

        sa.Column("status", sa.String(), nullable=False),
        sa.Column("failure_code", sa.String(), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),

        sa.Column("charged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_self_pay_charges_client_id", "self_pay_charges", ["client_id"])
    op.create_index("ix_self_pay_charges_visit_id", "self_pay_charges", ["visit_id"])
    op.create_index("ix_self_pay_charges_status", "self_pay_charges", ["status"])
    op.create_index("ix_self_pay_charges_payment_intent_id", "self_pay_charges", ["stripe_payment_intent_id"], unique=False)


def downgrade():
    op.drop_index("ix_self_pay_charges_payment_intent_id", table_name="self_pay_charges")
    op.drop_index("ix_self_pay_charges_status", table_name="self_pay_charges")
    op.drop_index("ix_self_pay_charges_visit_id", table_name="self_pay_charges")
    op.drop_index("ix_self_pay_charges_client_id", table_name="self_pay_charges")
    op.drop_table("self_pay_charges")