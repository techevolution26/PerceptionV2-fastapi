"""add perception reports and moderation workflow

Revision ID: 0011_perception_reports
Revises: 0010_saved_perceptions
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_perception_reports"
down_revision = "0010_saved_perceptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "perception_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reporter_user_id", sa.Integer(), nullable=False),
        sa.Column("perception_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("details", sa.String(length=2000), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["perception_id"], ["perceptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reporter_user_id", "perception_id", name="uq_perception_report_reporter_perception"),
    )
    op.create_index("ix_perception_reports_reporter_user_id", "perception_reports", ["reporter_user_id"])
    op.create_index("ix_perception_reports_perception_id", "perception_reports", ["perception_id"])
    op.create_index("ix_perception_reports_reviewed_by_user_id", "perception_reports", ["reviewed_by_user_id"])
    op.create_index("ix_perception_reports_created_at", "perception_reports", ["created_at"])
    op.create_index("ix_perception_reports_status_created", "perception_reports", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_perception_reports_status_created", table_name="perception_reports")
    op.drop_index("ix_perception_reports_created_at", table_name="perception_reports")
    op.drop_index("ix_perception_reports_reviewed_by_user_id", table_name="perception_reports")
    op.drop_index("ix_perception_reports_perception_id", table_name="perception_reports")
    op.drop_index("ix_perception_reports_reporter_user_id", table_name="perception_reports")
    op.drop_table("perception_reports")
