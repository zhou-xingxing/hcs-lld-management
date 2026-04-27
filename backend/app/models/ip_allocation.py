from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.time_utils import utcnow_db

if TYPE_CHECKING:
    from app.models.network_plane_type import NetworkPlaneType
    from app.models.region import Region
    from app.models.region_network_plane import RegionNetworkPlane


def gen_uuid() -> str:
    return str(uuid.uuid4())


class IPAllocation(Base):
    __tablename__ = "ip_allocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    region_id: Mapped[str] = mapped_column(String(36), ForeignKey("regions.id", ondelete="CASCADE"), index=True)
    plane_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("network_plane_types.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 归属的平面节点（精确到树中具体节点，而非仅 plane_type）
    # nullable=True 兼容旧数据；新创建的分配必须关联到具体平面节点
    plane_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("region_network_planes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    ip_range: Mapped[str] = mapped_column(String(43), nullable=False)
    vlan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gateway: Mapped[str | None] = mapped_column(String(39), nullable=True)
    subnet_mask: Mapped[str | None] = mapped_column(String(15), nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_db)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow_db, onupdate=utcnow_db)

    # relationships
    region: Mapped[Region] = relationship("Region", back_populates="allocations")
    plane_type: Mapped[NetworkPlaneType] = relationship("NetworkPlaneType", back_populates="allocations")
    plane: Mapped[RegionNetworkPlane | None] = relationship("RegionNetworkPlane", back_populates="allocations")
