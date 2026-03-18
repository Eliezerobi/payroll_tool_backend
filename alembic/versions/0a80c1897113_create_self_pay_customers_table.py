"""create self pay customers table

Revision ID: 0a80c1897113
Revises: 923b854af919
Create Date: 2026-03-09 19:05:30.877310
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0a80c1897113"
down_revision: Union[str, Sequence[str], None] = "923b854af919"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "SelfPayCustomers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.String(), nullable=False),
        sa.Column("monday_item_id", sa.String(), nullable=True),

        sa.Column("stripe_customer_id", sa.String(), nullable=False),
        sa.Column("stripe_checkout_session_id", sa.String(), nullable=False),
        sa.Column("stripe_setup_intent_id", sa.String(), nullable=True),
        sa.Column("stripe_payment_method_id", sa.String(), nullable=True),

        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),

        sa.Column("street", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("zip_code", sa.String(), nullable=True),

        sa.Column(
            "services",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),

        sa.Column(
            "cc_status",
            sa.String(),
            nullable=False,
            server_default=sa.text("'Waiting On CC'"),
        ),
        sa.Column(
            "setup_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),

        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_id"),
        sa.UniqueConstraint("stripe_checkout_session_id"),
    )

    op.create_index(op.f("ix_SelfPayCustomers_id"), "SelfPayCustomers", ["id"], unique=False)
    op.create_index(op.f("ix_SelfPayCustomers_lead_id"), "SelfPayCustomers", ["lead_id"], unique=False)
    op.create_index(op.f("ix_SelfPayCustomers_monday_item_id"), "SelfPayCustomers", ["monday_item_id"], unique=False)
    op.create_index(op.f("ix_SelfPayCustomers_stripe_customer_id"), "SelfPayCustomers", ["stripe_customer_id"], unique=False)
    op.create_index(op.f("ix_SelfPayCustomers_stripe_checkout_session_id"), "SelfPayCustomers", ["stripe_checkout_session_id"], unique=False)
    op.create_index(op.f("ix_SelfPayCustomers_stripe_setup_intent_id"), "SelfPayCustomers", ["stripe_setup_intent_id"], unique=False)
    op.create_index(op.f("ix_SelfPayCustomers_stripe_payment_method_id"), "SelfPayCustomers", ["stripe_payment_method_id"], unique=False)
    op.create_index(op.f("ix_SelfPayCustomers_email"), "SelfPayCustomers", ["email"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_SelfPayCustomers_email"), table_name="SelfPayCustomers")
    op.drop_index(op.f("ix_SelfPayCustomers_stripe_payment_method_id"), table_name="SelfPayCustomers")
    op.drop_index(op.f("ix_SelfPayCustomers_stripe_setup_intent_id"), table_name="SelfPayCustomers")
    op.drop_index(op.f("ix_SelfPayCustomers_stripe_checkout_session_id"), table_name="SelfPayCustomers")
    op.drop_index(op.f("ix_SelfPayCustomers_stripe_customer_id"), table_name="SelfPayCustomers")
    op.drop_index(op.f("ix_SelfPayCustomers_monday_item_id"), table_name="SelfPayCustomers")
    op.drop_index(op.f("ix_SelfPayCustomers_lead_id"), table_name="SelfPayCustomers")
    op.drop_index(op.f("ix_SelfPayCustomers_id"), table_name="SelfPayCustomers")
    op.drop_table("SelfPayCustomers")