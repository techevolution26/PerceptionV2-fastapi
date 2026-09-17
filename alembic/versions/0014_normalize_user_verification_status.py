"""Normalize approved user verification status to VERIFIED.

Revision ID: 0014_normalize_user_verification_status
Revises: 0013_investigation_threads
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_normalize_user_status"
down_revision = "0013_investigation_threads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE users "
            "SET verification_status = 'VERIFIED' "
            "WHERE verification_status = 'APPROVED'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE users "
            "SET verification_status = 'APPROVED' "
            "WHERE verification_status = 'VERIFIED'"
        )
    )
