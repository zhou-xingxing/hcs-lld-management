import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BackupConfig(Base):
    __tablename__ = "backup_configs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    enabled = Column(Boolean, nullable=False, default=False)
    frequency = Column(String(20), nullable=False, default="daily")
    schedule_hour = Column(Integer, nullable=False, default=2)
    schedule_minute = Column(Integer, nullable=False, default=0)
    schedule_weekday = Column(Integer, nullable=True, default=1)
    method = Column(String(30), nullable=False, default="local")
    local_path = Column(String(500), nullable=True)
    endpoint_url = Column(String(500), nullable=True)
    access_key = Column(String(200), nullable=True)
    secret_key = Column(String(500), nullable=True)
    bucket = Column(String(200), nullable=True)
    object_prefix = Column(String(300), nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class BackupRecord(Base):
    __tablename__ = "backup_records"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    status = Column(String(20), nullable=False, default="running")
    method = Column(String(30), nullable=False)
    target = Column(String(800), nullable=True)
    file_size = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    operator = Column(String(100), nullable=False, default="system")
    started_at = Column(DateTime, nullable=False, default=utcnow)
    finished_at = Column(DateTime, nullable=True)
