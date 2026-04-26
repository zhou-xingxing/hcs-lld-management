import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IPAllocation(Base):
    __tablename__ = "ip_allocations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    region_id = Column(String(36), ForeignKey("regions.id", ondelete="CASCADE"), nullable=False, index=True)
    plane_type_id = Column(
        String(36), ForeignKey("network_plane_types.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ip_range = Column(String(43), nullable=False)
    vlan_id = Column(Integer, nullable=True)
    gateway = Column(String(39), nullable=True)
    subnet_mask = Column(String(15), nullable=True)
    purpose = Column(Text, nullable=True, default="")
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    # relationships
    region = relationship("Region", back_populates="allocations")
    plane_type = relationship("NetworkPlaneType", back_populates="allocations")
