import uuid

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utcnow_db


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Region(Base):
    __tablename__ = "regions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow_db)
    updated_at = Column(DateTime, nullable=False, default=utcnow_db, onupdate=utcnow_db)

    # relationships
    region_planes = relationship("RegionNetworkPlane", back_populates="region", cascade="all, delete-orphan")
    allocations = relationship("IPAllocation", back_populates="region", cascade="all, delete-orphan")
