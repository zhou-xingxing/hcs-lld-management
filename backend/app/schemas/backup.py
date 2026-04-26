from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

BackupFrequency = Literal["daily", "weekly"]
BackupMethod = Literal["local", "object_storage"]


class BackupConfigUpdate(BaseModel):
    enabled: bool
    frequency: BackupFrequency = "daily"
    schedule_hour: int = Field(2, ge=0, le=23)
    schedule_minute: int = Field(0, ge=0, le=59)
    schedule_weekday: Optional[int] = Field(1, ge=1, le=7)
    method: BackupMethod = "local"
    local_path: Optional[str] = Field(None, max_length=500)
    endpoint_url: Optional[str] = Field(None, max_length=500)
    access_key: Optional[str] = Field(None, max_length=200)
    secret_key: Optional[str] = Field(None, max_length=500)
    bucket: Optional[str] = Field(None, max_length=200)
    object_prefix: Optional[str] = Field(None, max_length=300)

    @model_validator(mode="after")
    def validate_target(self) -> "BackupConfigUpdate":
        if self.frequency == "weekly" and self.schedule_weekday is None:
            raise ValueError("每周备份必须选择星期")
        if self.method == "local" and not self.local_path:
            raise ValueError("本地备份路径不能为空")
        if self.method == "object_storage":
            missing = []
            for field_name in ("endpoint_url", "access_key", "bucket"):
                if not getattr(self, field_name):
                    missing.append(field_name)
            if missing:
                raise ValueError(f"对象存储配置不完整: {', '.join(missing)}")
        return self


class BackupConfigResponse(BaseModel):
    id: str
    enabled: bool
    frequency: BackupFrequency
    schedule_hour: int
    schedule_minute: int
    schedule_weekday: Optional[int] = None
    method: BackupMethod
    local_path: Optional[str] = None
    endpoint_url: Optional[str] = None
    access_key: Optional[str] = None
    secret_key_configured: bool = False
    bucket: Optional[str] = None
    object_prefix: Optional[str] = None
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    created_at: str
    updated_at: str


class BackupRecordResponse(BaseModel):
    id: str
    status: str
    method: str
    target: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    operator: str
    started_at: str
    finished_at: Optional[str] = None
