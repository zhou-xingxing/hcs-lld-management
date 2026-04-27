"""users auth

Revision ID: d5e6f7a8b9c0
Revises: c1f0d7e8a6b9
Create Date: 2026-04-26 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c1f0d7e8a6b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)

    op.create_table(
        "user_regions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("region_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "region_id", name="uq_user_region"),
    )
    op.create_index(op.f("ix_user_regions_region_id"), "user_regions", ["region_id"], unique=False)
    op.create_index(op.f("ix_user_regions_user_id"), "user_regions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_regions_user_id"), table_name="user_regions")
    op.drop_index(op.f("ix_user_regions_region_id"), table_name="user_regions")
    op.drop_table("user_regions")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_table("users")
