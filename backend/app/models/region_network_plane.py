from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
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
    __table_args__ = (UniqueConstraint("region_id", "plane_type_id", name="uq_region_plane_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    region_id: Mapped[str] = mapped_column(String(36), ForeignKey("regions.id", ondelete="CASCADE"))
    plane_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("network_plane_types.id", ondelete="CASCADE"))
    # CIDR 网络地址段，如 "10.0.0.0/22"；nullable 兼容旧数据
    cidr: Mapped[str | None] = mapped_column(String(43), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_db)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_db, onupdate=utcnow_db)

    # relationships
    region: Mapped[Region] = relationship("Region", back_populates="region_planes")
    plane_type: Mapped[NetworkPlaneType] = relationship("NetworkPlaneType", back_populates="region_planes")
    # 此平面节点下的 IP 分配（级联删除：删平面时自动删关联分配）
    allocations: Mapped[list[IPAllocation]] = relationship(
        "IPAllocation", back_populates="plane", cascade="all, delete-orphan"
    )
