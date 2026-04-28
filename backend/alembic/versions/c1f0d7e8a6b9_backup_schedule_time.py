"""backup schedule time

Revision ID: c1f0d7e8a6b9
Revises: b4d2a901c7e3
Create Date: 2026-04-26 21:00:00.000000

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "c1f0d7e8a6b9"
down_revision: Union[str, None] = "b4d2a901c7e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
