"""move plane hierarchy to network plane types

Revision ID: g8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g8b9c0d1e2f3"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("network_plane_types", schema=None) as batch_op:
        batch_op.add_column(sa.Column("parent_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_network_plane_types_parent",
            "network_plane_types",
            ["parent_id"],
            ["id"],
            ondelete="SET NULL",
        )

    bind = op.get_bind()
    _promote_existing_region_tree_to_type_tree(bind)
    _deduplicate_region_planes(bind)

    with op.batch_alter_table("region_network_planes", schema=None) as batch_op:
        batch_op.drop_constraint("fk_rnp_parent", type_="foreignkey")
        batch_op.drop_column("parent_id")
        batch_op.create_unique_constraint("uq_region_plane_type", ["region_id", "plane_type_id"])


def downgrade() -> None:
    with op.batch_alter_table("region_network_planes", schema=None) as batch_op:
        batch_op.drop_constraint("uq_region_plane_type", type_="unique")
        batch_op.add_column(sa.Column("parent_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_rnp_parent",
            "region_network_planes",
            ["parent_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("network_plane_types", schema=None) as batch_op:
        batch_op.drop_constraint("fk_network_plane_types_parent", type_="foreignkey")
        batch_op.drop_column("parent_id")


def _promote_existing_region_tree_to_type_tree(bind: sa.Connection) -> None:
    rows = bind.execute(
        sa.text(
            """
            SELECT child.plane_type_id AS child_type_id, parent.plane_type_id AS parent_type_id
            FROM region_network_planes AS child
            JOIN region_network_planes AS parent ON child.parent_id = parent.id
            WHERE child.parent_id IS NOT NULL
              AND child.plane_type_id != parent.plane_type_id
            """
        )
    ).mappings()

    inferred: dict[str, set[str]] = {}
    for row in rows:
        inferred.setdefault(str(row["child_type_id"]), set()).add(str(row["parent_type_id"]))

    for child_type_id, parent_type_ids in inferred.items():
        if len(parent_type_ids) != 1:
            continue
        parent_type_id = next(iter(parent_type_ids))
        current_parent = bind.execute(
            sa.text("SELECT parent_id FROM network_plane_types WHERE id = :id"),
            {"id": child_type_id},
        ).scalar()
        if current_parent in (None, parent_type_id):
            bind.execute(
                sa.text("UPDATE network_plane_types SET parent_id = :parent_id WHERE id = :id"),
                {"parent_id": parent_type_id, "id": child_type_id},
            )


def _deduplicate_region_planes(bind: sa.Connection) -> None:
    rows = bind.execute(
        sa.text(
            """
            SELECT id, region_id, plane_type_id, parent_id, created_at
            FROM region_network_planes
            ORDER BY region_id, plane_type_id, parent_id IS NOT NULL, created_at, id
            """
        )
    ).mappings()

    keep_by_key: dict[tuple[str, str], str] = {}
    duplicate_ids: list[str] = []
    for row in rows:
        key = (str(row["region_id"]), str(row["plane_type_id"]))
        row_id = str(row["id"])
        keep_id = keep_by_key.get(key)
        if keep_id is None:
            keep_by_key[key] = row_id
            continue
        bind.execute(
            sa.text("UPDATE ip_allocations SET plane_id = :keep_id WHERE plane_id = :duplicate_id"),
            {"keep_id": keep_id, "duplicate_id": row_id},
        )
        duplicate_ids.append(row_id)

    for duplicate_id in duplicate_ids:
        bind.execute(sa.text("DELETE FROM region_network_planes WHERE id = :id"), {"id": duplicate_id})
