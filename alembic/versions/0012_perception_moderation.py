"""add perception intake moderation assessments

Revision ID: 0012_perception_moderation
Revises: 0011_perception_reports
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_perception_moderation"
down_revision = "0011_perception_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "perception_moderation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("perception_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="published"),
        sa.Column("risk_level", sa.String(length=32), nullable=False, server_default="none"),
        sa.Column("flags", sa.JSON(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.String(length=2000), nullable=True),
        sa.ForeignKeyConstraint(["perception_id"], ["perceptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("perception_id", name="uq_perception_moderation_perception"),
    )
    op.create_index("ix_perception_moderation_perception_id", "perception_moderation", ["perception_id"])
    op.create_index("ix_perception_moderation_reviewed_by_user_id", "perception_moderation", ["reviewed_by_user_id"])
    op.create_index("ix_perception_moderation_status_created", "perception_moderation", ["status", "checked_at"])


def downgrade() -> None:
    op.drop_index("ix_perception_moderation_status_created", table_name="perception_moderation")
    op.drop_index("ix_perception_moderation_reviewed_by_user_id", table_name="perception_moderation")
    op.drop_index("ix_perception_moderation_perception_id", table_name="perception_moderation")
    op.drop_table("perception_moderation")
