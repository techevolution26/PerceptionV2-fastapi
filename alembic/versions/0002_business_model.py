"""business model, subscriptions, verification and analytics

Revision ID: 0002_business_model
Revises: 0001_initial
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_business_model"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(32), nullable=False, server_default="USER"))
    op.add_column("users", sa.Column("professional_focus", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("country_code", sa.String(2), nullable=True))
    op.add_column("users", sa.Column("region", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("city", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("analytics_specialties", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("users", sa.Column("primary_analytics_topic_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("verification_status", sa.String(32), nullable=False, server_default="NOT_APPLIED"))
    op.add_column("users", sa.Column("verification_badge", sa.String(64), nullable=True))
    op.create_index("ix_users_country_code", "users", ["country_code"])
    op.create_index("ix_users_primary_analytics_topic_id", "users", ["primary_analytics_topic_id"])
    op.create_foreign_key(
        "fk_users_primary_analytics_topic",
        "users",
        "topics",
        ["primary_analytics_topic_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.String(1024), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("interval", sa.String(16), nullable=False, server_default="month"),
        sa.Column("analytics_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_topics", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verification_included", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("trial_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_plans_code", "plans", ["code"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("provider", sa.String(32), nullable=False, server_default="internal_trial"),
        sa.Column("provider_customer_id", sa.String(255), nullable=True),
        sa.Column("provider_subscription_id", sa.String(255), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])
    op.create_index("ix_subscriptions_user_status", "subscriptions", ["user_id", "status"])

    op.create_table(
        "user_analytics_topics",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "verification_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profession", sa.String(255), nullable=False),
        sa.Column("focus", sa.String(255), nullable=False),
        sa.Column("primary_topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_topic_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("badge", sa.String(64), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_verification_applications_user_id", "verification_applications", ["user_id"])
    op.create_index("ix_verification_user_status", "verification_applications", ["user_id", "status"])

    op.create_table(
        "perception_interactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("perception_id", sa.Integer(), sa.ForeignKey("perceptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("occurred_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_perception_interactions_actor_user_id", "perception_interactions", ["actor_user_id"])
    op.create_index("ix_interactions_perception_type", "perception_interactions", ["perception_id", "event_type"])
    op.create_index("ix_interactions_occurred_on", "perception_interactions", ["occurred_on"])
    op.create_unique_constraint(
        "uq_interaction_user_perception_type_day",
        "perception_interactions",
        ["actor_user_id", "perception_id", "event_type", "occurred_on"],
    )


def downgrade() -> None:
    op.drop_table("perception_interactions")
    op.drop_index("ix_verification_user_status", table_name="verification_applications")
    op.drop_index("ix_verification_applications_user_id", table_name="verification_applications")
    op.drop_table("verification_applications")
    op.drop_table("user_analytics_topics")
    op.drop_index("ix_subscriptions_user_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_plan_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_plans_code", table_name="plans")
    op.drop_table("plans")
    op.drop_constraint("fk_users_primary_analytics_topic", "users", type_="foreignkey")
    op.drop_index("ix_users_primary_analytics_topic_id", table_name="users")
    op.drop_index("ix_users_country_code", table_name="users")
    for column in [
        "verification_badge",
        "verification_status",
        "primary_analytics_topic_id",
        "analytics_specialties",
        "city",
        "region",
        "country_code",
        "professional_focus",
        "role",
    ]:
        op.drop_column("users", column)
