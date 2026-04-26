"""backup schedule time

Revision ID: c1f0d7e8a6b9
Revises: b4d2a901c7e3
Create Date: 2026-04-26 21:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c1f0d7e8a6b9"
down_revision: Union[str, None] = "b4d2a901c7e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("backup_configs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("schedule_hour", sa.Integer(), nullable=False, server_default="2"))
        batch_op.add_column(sa.Column("schedule_minute", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("schedule_weekday", sa.Integer(), nullable=True, server_default="1"))


def downgrade() -> None:
    with op.batch_alter_table("backup_configs", schema=None) as batch_op:
        batch_op.drop_column("schedule_weekday")
        batch_op.drop_column("schedule_minute")
        batch_op.drop_column("schedule_hour")
