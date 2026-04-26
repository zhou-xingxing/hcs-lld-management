from __future__ import annotations

import logging
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import BusinessError
from app.models.backup import BackupConfig, BackupRecord
from app.schemas.backup import BackupConfigUpdate
from app.services.change_log import log_change

logger = logging.getLogger(__name__)
BACKUP_FILENAME_PREFIX = "hcs_lld_data_backup"


def utcnow() -> datetime:
    """返回当前 UTC 时间。

    SQLAlchemy 当前模型使用不带时区的 DateTime，SQLite 读取后也会
    返回 naive datetime，因此备份服务内部统一使用 naive UTC。
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def calculate_next_run(
    base_time: datetime,
    frequency: str,
    schedule_hour: int,
    schedule_minute: int,
    schedule_weekday: Optional[int] = None,
) -> datetime:
    """计算下一次备份时间。

    Args:
        base_time: 计算基准时间。
        frequency: 备份周期，支持 daily 和 weekly。
        schedule_hour: 备份小时，0-23。
        schedule_minute: 备份分钟，0-59。
        schedule_weekday: 每周备份的星期，1 表示周一，7 表示周日。

    Returns:
        下一次应执行备份的 UTC 时间。

    Raises:
        BusinessError: 周期值不受支持。
    """
    candidate = base_time.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
    if frequency == "daily":
        if candidate <= base_time:
            candidate += timedelta(days=1)
        return candidate
    if frequency == "weekly":
        if schedule_weekday is None:
            raise BusinessError("每周备份必须选择星期")
        target_weekday = schedule_weekday - 1
        days_ahead = (target_weekday - base_time.weekday()) % 7
        candidate += timedelta(days=days_ahead)
        if candidate <= base_time:
            candidate += timedelta(weeks=1)
        return candidate
    raise BusinessError(f"Unsupported backup frequency: {frequency}")


def get_backup_config(db: Session) -> BackupConfig:
    """获取全局备份配置，不存在时创建默认配置。

    Args:
        db: 数据库会话。

    Returns:
        全局备份配置。
    """
    config = db.query(BackupConfig).order_by(BackupConfig.created_at.asc()).first()
    if config:
        return config

    config = BackupConfig(
        enabled=False,
        frequency="daily",
        schedule_hour=2,
        schedule_minute=0,
        schedule_weekday=1,
        method="local",
        local_path=settings.BACKUP_DEFAULT_LOCAL_PATH,
    )
    db.add(config)
    db.flush()
    return config


def update_backup_config(db: Session, data: BackupConfigUpdate, operator: str) -> BackupConfig:
    """更新全局备份配置。

    Args:
        db: 数据库会话。
        data: 新配置。
        operator: 操作者名称。

    Returns:
        更新后的备份配置。
    """
    config = get_backup_config(db)
    old_value = _config_snapshot(config)

    config.enabled = data.enabled
    config.frequency = data.frequency
    config.schedule_hour = data.schedule_hour
    config.schedule_minute = data.schedule_minute
    config.schedule_weekday = data.schedule_weekday if data.frequency == "weekly" else None
    config.method = data.method
    config.local_path = data.local_path
    config.endpoint_url = data.endpoint_url
    config.access_key = data.access_key
    config.secret_key = data.secret_key or (config.secret_key if data.method == "object_storage" else None)
    config.bucket = data.bucket
    config.object_prefix = data.object_prefix
    _validate_config(config)
    config.next_run_at = _next_run_from_config(config, utcnow()) if data.enabled else None
    db.flush()

    log_change(
        db,
        entity_type="backup_config",
        entity_id=config.id,
        action="update",
        operator=operator,
        old_value=old_value,
        new_value=_config_snapshot(config),
    )
    return config


def list_backup_records(db: Session, skip: int = 0, limit: int = 20) -> tuple[list[BackupRecord], int]:
    """查询备份执行历史。

    Args:
        db: 数据库会话。
        skip: 分页偏移量。
        limit: 每页条数。

    Returns:
        (备份记录列表, 总数) 的元组。
    """
    query = db.query(BackupRecord)
    total = query.count()
    records = query.order_by(BackupRecord.started_at.desc()).offset(skip).limit(limit).all()
    return records, total


def run_backup(db: Session, operator: str = "system", scheduled: bool = False) -> BackupRecord:
    """执行一次数据库备份。

    Args:
        db: 数据库会话。
        operator: 操作者名称。
        scheduled: 是否由定时任务触发。

    Returns:
        备份执行记录。

    Raises:
        BusinessError: 配置不完整或对象存储依赖不可用。
    """
    config = get_backup_config(db)
    _validate_config(config)

    record = BackupRecord(status="running", method=config.method, operator=operator or "system", started_at=utcnow())
    db.add(record)
    db.flush()

    backup_file: Optional[Path] = None
    try:
        backup_file = _create_sqlite_backup(db, config)
        file_size = backup_file.stat().st_size
        if config.method == "local":
            target = str(backup_file)
        else:
            target = _upload_object_storage(config, backup_file)
            backup_file.unlink(missing_ok=True)

        record.status = "success"
        record.target = target
        record.file_size = file_size
        record.finished_at = utcnow()
        config.last_run_at = record.finished_at
        if config.enabled:
            config.next_run_at = _next_run_from_config(config, record.finished_at)
        db.flush()

        log_change(
            db,
            entity_type="backup_config",
            entity_id=config.id,
            action="backup",
            operator=operator,
            new_value=target,
            comment="定时备份任务执行" if scheduled else "手动备份执行",
        )
    except Exception as exc:
        record.status = "failed"
        record.error_message = str(exc)
        record.finished_at = utcnow()
        if config.enabled:
            config.next_run_at = _next_run_from_config(config, record.finished_at)
        db.flush()
        if isinstance(exc, BusinessError):
            raise
        logger.exception("Backup failed")
    return record


def run_due_backup(db: Session) -> Optional[BackupRecord]:
    """执行已到期的定时备份任务。

    Args:
        db: 数据库会话。

    Returns:
        已执行的备份记录；未到期时返回 None。
    """
    config = get_backup_config(db)
    now = utcnow()
    if not config.enabled:
        return None
    if config.next_run_at is None:
        config.next_run_at = _next_run_from_config(config, now)
        db.flush()
    if config.next_run_at > now:
        return None
    return run_backup(db, operator="system", scheduled=True)


def _validate_config(config: BackupConfig) -> None:
    if config.frequency == "weekly" and config.schedule_weekday is None:
        raise BusinessError("每周备份必须选择星期")
    if config.method == "local" and not config.local_path:
        raise BusinessError("本地备份路径不能为空")
    if config.method == "object_storage":
        missing = []
        for field_name in ("endpoint_url", "access_key", "secret_key", "bucket"):
            if not getattr(config, field_name):
                missing.append(field_name)
        if missing:
            raise BusinessError(f"对象存储配置不完整: {', '.join(missing)}")


def _next_run_from_config(config: BackupConfig, base_time: datetime) -> datetime:
    return calculate_next_run(
        base_time,
        config.frequency,
        config.schedule_hour,
        config.schedule_minute,
        config.schedule_weekday,
    )


def _create_sqlite_backup(db: Session, config: BackupConfig) -> Path:
    timestamp = utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"{BACKUP_FILENAME_PREFIX}_{timestamp}.sqlite"
    target_dir = Path(config.local_path or settings.BACKUP_DEFAULT_LOCAL_PATH)
    if config.method == "object_storage":
        target_dir = Path(tempfile.gettempdir()) / "hcs_lld_backups"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename

    source = _get_sqlite_connection(db)
    dump_sql = "\n".join(source.iterdump())
    with sqlite3.connect(target_file) as target:
        target.executescript(dump_sql)
    return target_file


def _get_sqlite_connection(db: Session) -> sqlite3.Connection:
    raw_connection = db.connection().connection
    driver_connection = getattr(raw_connection, "driver_connection", raw_connection)
    if not isinstance(driver_connection, sqlite3.Connection):
        raise BusinessError("当前备份功能仅支持 SQLite 数据库")
    return driver_connection


def _upload_object_storage(config: BackupConfig, backup_file: Path) -> str:
    try:
        import boto3
    except ImportError as exc:
        raise BusinessError("对象存储备份需要安装 boto3 依赖") from exc

    prefix = (config.object_prefix or "").strip("/")
    object_key = f"{prefix}/{backup_file.name}" if prefix else backup_file.name
    client = boto3.client(
        "s3",
        endpoint_url=config.endpoint_url,
        aws_access_key_id=config.access_key,
        aws_secret_access_key=config.secret_key,
    )
    client.upload_file(str(backup_file), config.bucket, object_key)
    return f"s3://{config.bucket}/{object_key}"


def _config_snapshot(config: BackupConfig) -> str:
    secret_state = "configured" if config.secret_key else "empty"
    return (
        f"enabled={config.enabled};frequency={config.frequency};"
        f"schedule={config.schedule_weekday or ''} {config.schedule_hour:02d}:{config.schedule_minute:02d};"
        f"method={config.method};"
        f"local_path={config.local_path or ''};endpoint_url={config.endpoint_url or ''};"
        f"access_key={config.access_key or ''};secret_key={secret_state};"
        f"bucket={config.bucket or ''};object_prefix={config.object_prefix or ''}"
    )
