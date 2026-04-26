import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String, Text

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChangeLog(Base):
    __tablename__ = "change_logs"
    __table_args__ = (
        Index("idx_changelog_entity", "entity_type", "entity_id"),
        Index("idx_changelog_created", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    action = Column(String(20), nullable=False)
    field_name = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    operator = Column(String(100), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
