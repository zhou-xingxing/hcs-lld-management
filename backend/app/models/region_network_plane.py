import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RegionNetworkPlane(Base):
    __tablename__ = "region_network_planes"
    __table_args__ = (UniqueConstraint("region_id", "plane_type_id", name="uq_region_plane"),)

    id = Column(String(36), primary_key=True, default=gen_uuid)
    region_id = Column(String(36), ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)
    plane_type_id = Column(
        String(36), ForeignKey("network_plane_types.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, nullable=False, default=utcnow)

    # relationships
    region = relationship("Region", back_populates="region_planes")
    plane_type = relationship("NetworkPlaneType", back_populates="region_planes")
