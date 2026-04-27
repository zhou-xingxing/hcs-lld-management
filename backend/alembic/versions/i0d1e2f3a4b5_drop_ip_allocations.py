"""drop ip allocations

Revision ID: i0d1e2f3a4b5
Revises: h9c0d1e2f3a4
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i0d1e2f3a4b5"
down_revision: Union[str, None] = "h9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("ip_allocations")


def downgrade() -> None:
    op.create_table(
        "ip_allocations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("region_id", sa.String(length=36), nullable=False),
        sa.Column("plane_type_id", sa.String(length=36), nullable=False),
        sa.Column("plane_id", sa.String(length=36), nullable=True),
        sa.Column("ip_range", sa.String(length=43), nullable=False),
        sa.Column("vlan_id", sa.Integer(), nullable=True),
        sa.Column("gateway", sa.String(length=39), nullable=True),
        sa.Column("subnet_mask", sa.String(length=15), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["plane_id"], ["region_network_planes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plane_type_id"], ["network_plane_types.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ip_allocations_plane_id", "ip_allocations", ["plane_id"], unique=False)
    op.create_index("ix_ip_allocations_plane_type_id", "ip_allocations", ["plane_type_id"], unique=False)
    op.create_index("ix_ip_allocations_region_id", "ip_allocations", ["region_id"], unique=False)
