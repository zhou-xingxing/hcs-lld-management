from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, overload
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings

UTC = timezone.utc


def utcnow() -> datetime:
    """返回 timezone-aware UTC 当前时间。"""
    return datetime.now(UTC)


def utcnow_db() -> datetime:
    """返回用于数据库存储的 naive UTC 当前时间。"""
    return to_db_datetime(utcnow())


def to_utc(value: datetime) -> datetime:
    """将 datetime 统一转换为 timezone-aware UTC。

    SQLite 读取 DateTime 时会返回 naive datetime；项目约定所有 naive
    datetime 均表示 UTC。
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_db_datetime(value: datetime) -> datetime:
    """将 datetime 转为数据库存储使用的 naive UTC。"""
    return to_utc(value).replace(tzinfo=None)


# 帮助类型检查器区分：datetime 返回 str，None 返回 None。
@overload
def format_datetime(value: datetime) -> str: ...


@overload
def format_datetime(value: None) -> None: ...


def format_datetime(value: Optional[datetime]) -> Optional[str]:
    """将数据库或应用 datetime 格式化为带 UTC 时区的 ISO 8601 字符串。"""
    if value is None:
        return None
    return to_utc(value).isoformat()


def app_timezone() -> ZoneInfo:
    """返回系统配置的业务时区。"""
    try:
        return ZoneInfo(settings.APP_TIMEZONE)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Invalid APP_TIMEZONE: {settings.APP_TIMEZONE}") from exc
