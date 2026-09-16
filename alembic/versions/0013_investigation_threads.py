"""add private investigation threads

Revision ID: 0013_investigation_threads
Revises: 0012_perception_moderation
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_investigation_threads"
down_revision = "0012_perception_moderation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investigation_threads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("perception_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("question", sa.String(length=2000), nullable=False),
        sa.Column("rationale", sa.String(length=2000), nullable=False),
        sa.Column("evidence_basis", sa.String(length=1000), nullable=False),
        sa.Column("validation_step", sa.String(length=2000), nullable=False),
        sa.Column("evidence_trace_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["perception_id"], ["perceptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "perception_id", "question", name="uq_investigation_thread_user_perception_question"),
    )
    op.create_index("ix_investigation_threads_user_id", "investigation_threads", ["user_id"])
    op.create_index("ix_investigation_threads_perception_id", "investigation_threads", ["perception_id"])
    op.create_index("ix_investigation_threads_user_updated", "investigation_threads", ["user_id", "updated_at"])


def downgrade() -> None:
    op.drop_index("ix_investigation_threads_user_updated", table_name="investigation_threads")
    op.drop_index("ix_investigation_threads_perception_id", table_name="investigation_threads")
    op.drop_index("ix_investigation_threads_user_id", table_name="investigation_threads")
    op.drop_table("investigation_threads")
