"""add structured professional identity fields"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision = "0006_prof_identity_tax"
down_revision = "0005_google_oauth_support"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "professional_industries",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "professional_roles",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("primary_professional_role", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "verified_professional_roles",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.create_index(
        "ix_users_primary_professional_role",
        "users",
        ["primary_professional_role"],
        unique=False,
    )
    op.add_column(
        "verification_applications",
        sa.Column(
            "industry_codes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
        ),
    )
    op.add_column(
        "verification_applications",
        sa.Column(
            "professional_role_codes",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "verification_applications",
        sa.Column("primary_professional_role", sa.String(length=128), nullable=True),
    )
    op.alter_column("verification_applications", "industry_codes", server_default=None)
    op.alter_column(
        "verification_applications", "professional_role_codes", server_default=None
    )
    op.alter_column("users", "professional_industries", server_default=None)
    op.alter_column("users", "professional_roles", server_default=None)
    op.alter_column("users", "verified_professional_roles", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_users_primary_professional_role", table_name="users")
    op.drop_column("users", "verified_professional_roles")
    op.drop_column("users", "primary_professional_role")
    op.drop_column("users", "professional_roles")
    op.drop_column("verification_applications", "primary_professional_role")
    op.drop_column("verification_applications", "professional_role_codes")
    op.drop_column("verification_applications", "industry_codes")
    op.drop_column("users", "professional_industries")
