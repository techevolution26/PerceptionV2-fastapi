"""add saved perceptions

Revision ID: 0010_saved_perceptions
Revises: 0009_user_preferences
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_saved_perceptions"
down_revision = "0009_user_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_perceptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("perception_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["perception_id"], ["perceptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "perception_id", name="uq_saved_perception_user_perception"
        ),
    )
    op.create_index("ix_saved_perceptions_user_id", "saved_perceptions", ["user_id"], unique=False)
    op.create_index("ix_saved_perceptions_perception_id", "saved_perceptions", ["perception_id"], unique=False)
    op.create_index("ix_saved_perceptions_user_created", "saved_perceptions", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_saved_perceptions_user_created", table_name="saved_perceptions")
    op.drop_index("ix_saved_perceptions_perception_id", table_name="saved_perceptions")
    op.drop_index("ix_saved_perceptions_user_id", table_name="saved_perceptions")
    op.drop_table("saved_perceptions")
