from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import BusinessError
from app.models.backup import BackupConfig, BackupRecord
from app.schemas.backup import BackupConfigResponse, BackupConfigUpdate, BackupRecordResponse
from app.schemas.common import PaginatedResponse
from app.services.backup import get_backup_config, list_backup_records, run_backup, update_backup_config

router = APIRouter(prefix="/api/backup", tags=["Backup"])


def get_operator(x_operator: str = Header("system")) -> str:
    return x_operator


@router.get("/config", response_model=BackupConfigResponse)
def get_config_endpoint(db: Session = Depends(get_db)) -> BackupConfigResponse:
    """获取全局备份配置。"""
    config = get_backup_config(db)
    db.commit()
    return _to_config_response(config)


@router.put("/config", response_model=BackupConfigResponse)
def update_config_endpoint(
    data: BackupConfigUpdate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
) -> BackupConfigResponse:
    """更新全局备份配置。"""
    try:
        config = update_backup_config(db, data, operator)
    except BusinessError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    return _to_config_response(config)


@router.post("/run", response_model=BackupRecordResponse, status_code=201)
def run_backup_endpoint(
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
) -> BackupRecordResponse:
    """立即执行一次备份。"""
    try:
        record = run_backup(db, operator=operator, scheduled=False)
    except BusinessError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    return _to_record_response(record)


@router.get("/records", response_model=PaginatedResponse[BackupRecordResponse])
def list_records_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse[BackupRecordResponse]:
    """查询备份执行历史。"""
    records, total = list_backup_records(db, skip=skip, limit=limit)
    return PaginatedResponse(
        items=[_to_record_response(record) for record in records],
        total=total,
        skip=skip,
        limit=limit,
    )


def _format_dt(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


def _to_config_response(config: BackupConfig) -> BackupConfigResponse:
    return BackupConfigResponse(
        id=config.id,
        enabled=config.enabled,
        frequency=config.frequency,
        schedule_hour=config.schedule_hour,
        schedule_minute=config.schedule_minute,
        schedule_weekday=config.schedule_weekday,
        method=config.method,
        local_path=config.local_path,
        endpoint_url=config.endpoint_url,
        access_key=config.access_key,
        secret_key_configured=bool(config.secret_key),
        bucket=config.bucket,
        object_prefix=config.object_prefix,
        last_run_at=_format_dt(config.last_run_at),
        next_run_at=_format_dt(config.next_run_at),
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


def _to_record_response(record: BackupRecord) -> BackupRecordResponse:
    return BackupRecordResponse(
        id=record.id,
        status=record.status,
        method=record.method,
        target=record.target,
        file_size=record.file_size,
        error_message=record.error_message,
        operator=record.operator,
        started_at=record.started_at.isoformat(),
        finished_at=_format_dt(record.finished_at),
    )
