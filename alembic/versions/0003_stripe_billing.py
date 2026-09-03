"""add Stripe billing state and idempotent webhook events

Revision ID: 0003_stripe_billing
Revises: 0002_business_model
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_stripe_billing"
down_revision: Union[str, None] = "0002_business_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("billing_customer_id", sa.String(255), nullable=True))
    op.create_index("ix_users_billing_customer_id", "users", ["billing_customer_id"], unique=True)

    op.add_column("plans", sa.Column("stripe_price_id", sa.String(255), nullable=True))
    op.create_index("ix_plans_stripe_price_id", "plans", ["stripe_price_id"], unique=True)

    op.add_column("subscriptions", sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("subscriptions", sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True))
    op.add_column("subscriptions", sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("subscriptions", sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "billing_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_billing_event_provider_id"),
    )


def downgrade() -> None:
    op.drop_table("billing_events")
    op.drop_column("subscriptions", "canceled_at")
    op.drop_column("subscriptions", "cancel_at_period_end")
    op.drop_column("subscriptions", "current_period_end")
    op.drop_column("subscriptions", "current_period_start")
    op.drop_index("ix_plans_stripe_price_id", table_name="plans")
    op.drop_column("plans", "stripe_price_id")
    op.drop_index("ix_users_billing_customer_id", table_name="users")
    op.drop_column("users", "billing_customer_id")
