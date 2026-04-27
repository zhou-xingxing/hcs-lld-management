"""add gateway fields to region network planes

Revision ID: h9c0d1e2f3a4
Revises: g8b9c0d1e2f3
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h9c0d1e2f3a4"
down_revision: Union[str, None] = "g8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("region_network_planes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("vlan_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("gateway_position", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("gateway_ip", sa.String(length=39), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("region_network_planes", schema=None) as batch_op:
        batch_op.drop_column("gateway_ip")
        batch_op.drop_column("gateway_position")
        batch_op.drop_column("vlan_id")
