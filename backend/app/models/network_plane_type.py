import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NetworkPlaneType(Base):
    __tablename__ = "network_plane_types"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)

    # relationships
    region_planes = relationship("RegionNetworkPlane", back_populates="plane_type")
    allocations = relationship("IPAllocation", back_populates="plane_type")
