"""make password nullable for google oauth support"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision = "0005_google_oauth_support"
down_revision = "0004_security_messaging"
branch_labels = None
depends_on = None


def upgrade():
    # Make password_hash nullable to support Google OAuth users without password
    op.alter_column("users", "password", existing_type=sa.String(255), nullable=True)


def downgrade():
    # Revert to NOT NULL (downgrade only works if no NULL passwords exist)
    op.alter_column("users", "password", existing_type=sa.String(255), nullable=False)
