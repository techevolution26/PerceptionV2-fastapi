"""add user notification and privacy preferences

Revision ID: 0009_user_preferences
Revises: 0008_comment_intelligence
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_user_preferences"
down_revision = "0008_comment_intelligence"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("users", sa.Column("notification_preferences", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("users", sa.Column("privacy_preferences", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.alter_column("users", "notification_preferences", server_default=None)
    op.alter_column("users", "privacy_preferences", server_default=None)

def downgrade() -> None:
    op.drop_column("users", "privacy_preferences")
    op.drop_column("users", "notification_preferences")
