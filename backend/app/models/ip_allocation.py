import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utcnow_db


def gen_uuid() -> str:
    return str(uuid.uuid4())


class IPAllocation(Base):
    __tablename__ = "ip_allocations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    region_id = Column(String(36), ForeignKey("regions.id", ondelete="CASCADE"), nullable=False, index=True)
    plane_type_id = Column(
        String(36), ForeignKey("network_plane_types.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 归属的平面节点（精确到树中具体节点，而非仅 plane_type）
    # nullable=True 兼容旧数据；新创建的分配必须关联到具体平面节点
    plane_id = Column(String(36), ForeignKey("region_network_planes.id", ondelete="CASCADE"), nullable=True, index=True)
    ip_range = Column(String(43), nullable=False)
    vlan_id = Column(Integer, nullable=True)
    gateway = Column(String(39), nullable=True)
    subnet_mask = Column(String(15), nullable=True)
    purpose = Column(Text, nullable=True, default="")
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=utcnow_db)
    updated_at = Column(DateTime, nullable=False, default=utcnow_db, onupdate=utcnow_db)

    # relationships
    region = relationship("Region", back_populates="allocations")
    plane_type = relationship("NetworkPlaneType", back_populates="allocations")
    plane = relationship("RegionNetworkPlane", back_populates="allocations")
