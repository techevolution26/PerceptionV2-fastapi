"""add comment intelligence result storage

Revision ID: 0008_comment_intelligence
Revises: 0007_password_recovery
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_comment_intelligence"
down_revision = "0007_password_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "comment_intelligence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sentiment", sa.String(length=32), nullable=True),
        sa.Column("stance", sa.String(length=32), nullable=True),
        sa.Column("themes", sa.JSON(), nullable=False),
        sa.Column("is_question", sa.Boolean(), nullable=False),
        sa.Column("has_concern", sa.Boolean(), nullable=False),
        sa.Column("agreement_signal", sa.Boolean(), nullable=False),
        sa.Column("disagreement_signal", sa.Boolean(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(length=128), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("comment_id", name="uq_comment_intelligence_comment"),
    )
    op.create_index(
        "ix_comment_intelligence_comment_id", "comment_intelligence", ["comment_id"]
    )
    op.create_index(
        "ix_comment_intelligence_status", "comment_intelligence", ["status"]
    )
    op.create_index(
        "ix_comment_intelligence_model_version",
        "comment_intelligence",
        ["model_version"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_comment_intelligence_model_version", table_name="comment_intelligence"
    )
    op.drop_index("ix_comment_intelligence_status", table_name="comment_intelligence")
    op.drop_index(
        "ix_comment_intelligence_comment_id", table_name="comment_intelligence"
    )
    op.drop_table("comment_intelligence")
