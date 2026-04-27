from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.time_utils import utcnow_db

if TYPE_CHECKING:
    from app.models.ip_allocation import IPAllocation
    from app.models.network_plane_type import NetworkPlaneType
    from app.models.region import Region


def gen_uuid() -> str:
    return str(uuid.uuid4())


class RegionNetworkPlane(Base):
    __tablename__ = "region_network_planes"
    # 数据库级唯一约束已移除，改为应用层校验：
    # 同一 (region_id, plane_type_id) 最多一个 root 节点 (parent_id IS NULL)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    region_id: Mapped[str] = mapped_column(String(36), ForeignKey("regions.id", ondelete="CASCADE"))
    plane_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("network_plane_types.id", ondelete="CASCADE"))
    # CIDR 网络地址段，如 "10.0.0.0/22"；nullable 兼容旧数据
    cidr: Mapped[str | None] = mapped_column(String(43), nullable=True)
    # 父平面节点 ID，自引用 FK；nullable 表示根节点
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("region_network_planes.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_db)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_db, onupdate=utcnow_db)

    # relationships
    region: Mapped[Region] = relationship("Region", back_populates="region_planes")
    plane_type: Mapped[NetworkPlaneType] = relationship("NetworkPlaneType", back_populates="region_planes")
    # 父平面（自引用）
    parent: Mapped[RegionNetworkPlane | None] = relationship(
        "RegionNetworkPlane", remote_side="RegionNetworkPlane.id", back_populates="children"
    )
    # 子平面列表（级联删除：删父平面时自动删子平面及其 IP 分配）
    children: Mapped[list[RegionNetworkPlane]] = relationship(
        "RegionNetworkPlane", back_populates="parent", cascade="all, delete-orphan"
    )
    # 此平面节点下的 IP 分配（级联删除：删平面时自动删关联分配）
    allocations: Mapped[list[IPAllocation]] = relationship(
        "IPAllocation", back_populates="plane", cascade="all, delete-orphan"
    )
