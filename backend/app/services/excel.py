from __future__ import annotations

import json
import uuid
from datetime import timedelta
from threading import Lock
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.ip_allocation import IPAllocation
from app.services.change_log import log_change
from app.utils.excel_utils import parse_excel
from app.utils.ip_utils import find_overlapping, parse_cidr
from app.utils.time_utils import utcnow

# In-memory import preview cache
_import_cache: dict[str, dict[str, Any]] = {}
_import_cache_lock = Lock()
_IMPORT_TTL = timedelta(minutes=30)


def store_preview(rows: list[dict[str, Any]]) -> str:
    """存储导入预览数据到内存缓存。

    数据在缓存中保留 _IMPORT_TTL（30 分钟），超时后自动失效。

    Args:
        rows: 解析后的行数据列表。

    Returns:
        预览数据的唯一标识 ID（UUID4 字符串）。
    """
    preview_id = str(uuid.uuid4())
    with _import_cache_lock:
        _import_cache[preview_id] = {
            "rows": rows,
            "created_at": utcnow(),
        }
    return preview_id


def get_preview(preview_id: str) -> Optional[list[dict[str, Any]]]:
    """从内存缓存中获取导入预览数据。

    Args:
        preview_id: 预览数据 ID。

    Returns:
        预览的行数据列表，已过期或不存在时返回 None。
    """
    with _import_cache_lock:
        entry = _import_cache.get(preview_id)
        if entry and utcnow() - entry["created_at"] < _IMPORT_TTL:
            return entry["rows"]  # type: ignore[no-any-return]
        _import_cache.pop(preview_id, None)
        return None


def get_preview_region_ids(preview_id: str) -> Optional[set[str]]:
    """Return Region IDs covered by a cached import preview."""
    rows = get_preview(preview_id)
    if rows is None:
        return None
    return {str(row["_region_id"]) for row in rows}


def preview_import(file_bytes: bytes, db: Session) -> dict[str, Any]:
    """解析导入文件并校验数据，返回预览结果。

    校验内容：Region 和网络平面类型是否存在、是否已启用、
    CIDR 格式、状态值是否合法。

    Args:
        file_bytes: Excel 文件的二进制内容。
        db: 数据库会话。

    Returns:
        包含 preview_id、total_rows、valid_rows、error_rows 及
        每行详细数据的预览结果字典。
    """
    from app.models.network_plane_type import NetworkPlaneType
    from app.models.region import Region
    from app.models.region_network_plane import RegionNetworkPlane

    parsed_rows = parse_excel(file_bytes)
    valid_rows = []
    error_rows = []

    # Preload lookup data
    all_regions = {r.name: r.id for r in db.query(Region).all()}
    all_plane_types = {pt.name: pt.id for pt in db.query(NetworkPlaneType).all()}
    enabled_planes = {(rp.region_id, rp.plane_type_id) for rp in db.query(RegionNetworkPlane).all()}

    for row in parsed_rows:
        row_errors = []
        region_id = all_regions.get(row["region_name"])
        plane_type_id = all_plane_types.get(row["plane_type_name"])

        if not region_id:
            row_errors.append(f"区域不存在: {row['region_name']}")
        if not plane_type_id:
            row_errors.append(f"网络平面类型不存在: {row['plane_type_name']}")
        if region_id and plane_type_id:
            if (region_id, plane_type_id) not in enabled_planes:
                row_errors.append(f"区域未启用该网络平面: {row['region_name']}/{row['plane_type_name']}")

        if not row["ip_range"]:
            row_errors.append("IP地址段不能为空")
        else:
            net = parse_cidr(row["ip_range"])
            if not net:
                row_errors.append(f"无效CIDR: {row['ip_range']}")

        # Validate status
        if row["status"] not in ("active", "reserved", "deprecated"):
            row_errors.append(f"无效状态值: {row['status']}")

        if row_errors:
            error_rows.append({"row": row["row_number"], "errors": row_errors})
        else:
            valid_rows.append(
                {
                    **row,
                    "_region_id": region_id,
                    "_plane_type_id": plane_type_id,
                }
            )

    preview_id = store_preview(valid_rows)

    return {
        "preview_id": preview_id,
        "total_rows": len(parsed_rows),
        "valid_rows": len(valid_rows),
        "error_rows": error_rows,
        "rows": [
            {
                "row_number": r["row_number"],
                "region_name": r["region_name"],
                "plane_type_name": r["plane_type_name"],
                "ip_range": r["ip_range"],
                "vlan_id": r["vlan_id"],
                "gateway": r["gateway"],
                "subnet_mask": r["subnet_mask"],
                "purpose": r["purpose"],
                "status": r["status"],
            }
            for r in parsed_rows
        ],
    }


def confirm_import(preview_id: str, operator: str, db: Session) -> dict[str, Any]:
    """确认执行导入，将预览数据写入数据库。

    逐行写入，每行都会与已有分配做重叠检测。
    已过期的预览数据会被拒绝导入。

    Args:
        preview_id: 预览数据 ID。
        operator: 操作者名称。
        db: 数据库会话。

    Returns:
        包含 success、imported_count、error_count、errors 的导入结果字典。
    """
    rows = get_preview(preview_id)
    if not rows:
        return {
            "success": False,
            "imported_count": 0,
            "error_count": 0,
            "errors": [{"row": 0, "errors": ["预览数据已过期，请重新上传"]}],
        }

    imported = 0
    errors = []

    for row in rows:
        try:
            # Check overlap against existing allocations in the same region+plane
            existing_cidrs = [
                r[0]
                for r in db.query(IPAllocation.ip_range)
                .filter(
                    IPAllocation.region_id == row["_region_id"],
                    IPAllocation.plane_type_id == row["_plane_type_id"],
                )
                .all()
            ]
            overlapped = find_overlapping(row["ip_range"], existing_cidrs)
            if overlapped:
                errors.append({"row": row["row_number"], "errors": [f"与现有分配重叠: {', '.join(overlapped)}"]})
                continue

            allocation = IPAllocation(
                region_id=row["_region_id"],
                plane_type_id=row["_plane_type_id"],
                ip_range=row["ip_range"],
                vlan_id=row["vlan_id"],
                gateway=row.get("gateway"),
                subnet_mask=row.get("subnet_mask"),
                purpose=row.get("purpose", ""),
                status=row.get("status", "active"),
            )
            db.add(allocation)
            db.flush()

            log_change(
                db,
                entity_type="ip_allocation",
                entity_id=allocation.id,
                action="import",
                operator=operator,
                new_value=json.dumps(
                    {
                        "ip_range": row["ip_range"],
                        "region_id": row["_region_id"],
                        "plane_type_id": row["_plane_type_id"],
                    }
                ),
                comment="Excel批量导入",
            )
            imported += 1
        except Exception as e:
            errors.append({"row": row["row_number"], "errors": [str(e)]})

    db.commit()
    return {
        "success": True,
        "imported_count": imported,
        "error_count": len(errors),
        "errors": errors,
    }
