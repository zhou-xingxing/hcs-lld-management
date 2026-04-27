import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utcnow_db


def gen_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user", index=True)
    display_name = Column(String(100), nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utcnow_db)
    updated_at = Column(DateTime, nullable=False, default=utcnow_db, onupdate=utcnow_db)

    region_links = relationship("UserRegion", back_populates="user", cascade="all, delete-orphan")


class UserRegion(Base):
    __tablename__ = "user_regions"
    __table_args__ = (UniqueConstraint("user_id", "region_id", name="uq_user_region"),)

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    region_id = Column(String(36), ForeignKey("regions.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow_db)

    user = relationship("User", back_populates="region_links")
    region = relationship("Region")
