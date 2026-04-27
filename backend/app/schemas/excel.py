from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ImportRow(BaseModel):
    row_number: int
    region_name: str
    plane_type_name: str
    ip_range: str
    vlan_id: Optional[int] = None
    gateway: Optional[str] = None
    subnet_mask: Optional[str] = None
    purpose: Optional[str] = ""
    status: str = "active"


class ImportError(BaseModel):
    row: int
    errors: list[str]


class ImportPreviewResponse(BaseModel):
    preview_id: str
    total_rows: int
    valid_rows: int
    error_rows: list[ImportError]
    rows: list[ImportRow]


class ImportConfirmRequest(BaseModel):
    preview_id: str


class ImportResultResponse(BaseModel):
    success: bool
    imported_count: int
    error_count: int
    errors: list[ImportError]


class StatsResponse(BaseModel):
    total_regions: int
    total_plane_types: int
    total_allocations: int
    total_change_logs: int
    allocation_by_status: dict[str, int]
    allocation_by_region: list[dict[str, Any]]
    recent_changes: list[dict[str, Any]]
