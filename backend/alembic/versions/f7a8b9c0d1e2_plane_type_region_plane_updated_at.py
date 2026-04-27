"""network plane type and region plane updated_at

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("network_plane_types", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
        )

    with op.batch_alter_table("region_network_planes", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
        )


def downgrade() -> None:
    with op.batch_alter_table("region_network_planes", schema=None) as batch_op:
        batch_op.drop_column("updated_at")

    with op.batch_alter_table("network_plane_types", schema=None) as batch_op:
        batch_op.drop_column("updated_at")
