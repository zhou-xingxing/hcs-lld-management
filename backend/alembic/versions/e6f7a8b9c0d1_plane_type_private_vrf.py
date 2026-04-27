"""network plane type private and vrf fields

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("network_plane_types", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("vrf", sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("network_plane_types", schema=None) as batch_op:
        batch_op.drop_column("vrf")
        batch_op.drop_column("is_private")
