"""rename user region grants to permissions

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-05-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, None] = "j1k2l3m4n5o6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("user_regions", "user_region_permissions")
    op.drop_index(op.f("ix_user_regions_user_id"), table_name="user_region_permissions")
    op.drop_index(op.f("ix_user_regions_region_id"), table_name="user_region_permissions")

    with op.batch_alter_table("user_region_permissions", schema=None) as batch_op:
        batch_op.drop_constraint("uq_user_region", type_="unique")
        batch_op.create_unique_constraint("uq_user_region_permission", ["user_id", "region_id"])

    op.create_index(
        op.f("ix_user_region_permissions_user_id"),
        "user_region_permissions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_region_permissions_region_id"),
        "user_region_permissions",
        ["region_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_region_permissions_region_id"), table_name="user_region_permissions")
    op.drop_index(op.f("ix_user_region_permissions_user_id"), table_name="user_region_permissions")

    with op.batch_alter_table("user_region_permissions", schema=None) as batch_op:
        batch_op.drop_constraint("uq_user_region_permission", type_="unique")
        batch_op.create_unique_constraint("uq_user_region", ["user_id", "region_id"])

    op.rename_table("user_region_permissions", "user_regions")
    op.create_index(op.f("ix_user_regions_region_id"), "user_regions", ["region_id"], unique=False)
    op.create_index(op.f("ix_user_regions_user_id"), "user_regions", ["user_id"], unique=False)
