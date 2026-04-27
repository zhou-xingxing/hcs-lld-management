"""add scope to region network planes

Revision ID: j1k2l3m4n5o6
Revises: i0d1e2f3a4b5
Create Date: 2026-04-28 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "j1k2l3m4n5o6"
down_revision: Union[str, None] = "i0d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("region_network_planes", schema=None) as batch_op:
        batch_op.drop_constraint("uq_region_plane_type", type_="unique")
        batch_op.add_column(sa.Column("scope", sa.String(length=100), nullable=False, server_default="Global"))
        batch_op.create_unique_constraint("uq_region_plane_type_scope", ["region_id", "plane_type_id", "scope"])


def downgrade() -> None:
    with op.batch_alter_table("region_network_planes", schema=None) as batch_op:
        batch_op.drop_constraint("uq_region_plane_type_scope", type_="unique")
        batch_op.drop_column("scope")
        batch_op.create_unique_constraint("uq_region_plane_type", ["region_id", "plane_type_id"])
