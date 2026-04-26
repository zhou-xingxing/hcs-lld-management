"""multilevel network plane

网络平面支持多级树状结构：
- region_network_planes: 新增 cidr, parent_id 字段，移除唯一约束
- ip_allocations: 新增 plane_id 字段

Revision ID: af3e9c2b8d14
Revises: c9ce20c8a1b2
Create Date: 2026-04-26 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af3e9c2b8d14'
down_revision: Union[str, None] = 'c9ce20c8a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === RegionNetworkPlane 表变更 ===
    with op.batch_alter_table('region_network_planes', schema=None) as batch_op:
        # 新增 CIDR 字段（nullable 兼容旧数据）
        batch_op.add_column(sa.Column('cidr', sa.String(length=43), nullable=True))
        # 新增父节点自引用外键（nullable 表示根节点）
        batch_op.add_column(sa.Column('parent_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            'fk_rnp_parent', 'region_network_planes',
            ['parent_id'], ['id'], ondelete='CASCADE'
        )
        # 移除旧的唯一约束 (region_id, plane_type_id)
        batch_op.drop_constraint('uq_region_plane', type_='unique')

    # === IPAllocation 表变更 ===
    with op.batch_alter_table('ip_allocations', schema=None) as batch_op:
        # 新增 plane_id 字段（nullable 兼容旧数据）
        batch_op.add_column(sa.Column('plane_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            'fk_ia_plane', 'region_network_planes',
            ['plane_id'], ['id'], ondelete='CASCADE'
        )
        batch_op.create_index('ix_ip_allocations_plane_id', ['plane_id'], unique=False)


def downgrade() -> None:
    # === IPAllocation 表回退 ===
    with op.batch_alter_table('ip_allocations', schema=None) as batch_op:
        batch_op.drop_index('ix_ip_allocations_plane_id')
        batch_op.drop_constraint('fk_ia_plane', type_='foreignkey')
        batch_op.drop_column('plane_id')

    # === RegionNetworkPlane 表回退 ===
    with op.batch_alter_table('region_network_planes', schema=None) as batch_op:
        # 恢复唯一约束
        batch_op.create_unique_constraint('uq_region_plane', ['region_id', 'plane_type_id'])
        batch_op.drop_constraint('fk_rnp_parent', type_='foreignkey')
        batch_op.drop_column('parent_id')
        batch_op.drop_column('cidr')
