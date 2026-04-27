from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.exceptions import BusinessError
from app.models.network_plane_type import NetworkPlaneType
from app.models.region_network_plane import RegionNetworkPlane
from app.schemas.network_plane_type import PlaneTypeCreate, PlaneTypeUpdate
from app.services.change_log import log_change


def list_plane_types(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[NetworkPlaneType], int]:
    """查询网络平面类型列表。

    Args:
        db: 数据库会话。
        skip: 分页偏移量。
        limit: 每页条数。

    Returns:
        (平面类型列表, 总数) 的元组。
    """
    total = db.query(NetworkPlaneType).count()
    items = db.query(NetworkPlaneType).order_by(NetworkPlaneType.created_at.asc()).offset(skip).limit(limit).all()
    return items, total


def get_plane_type(db: Session, pt_id: str) -> Optional[NetworkPlaneType]:
    """根据 ID 获取网络平面类型。

    Args:
        db: 数据库会话。
        pt_id: 平面类型 ID。

    Returns:
        NetworkPlaneType 对象，不存在时返回 None。
    """
    return db.query(NetworkPlaneType).filter(NetworkPlaneType.id == pt_id).first()


def get_plane_type_by_name(db: Session, name: str) -> Optional[NetworkPlaneType]:
    """根据名称获取网络平面类型。

    Args:
        db: 数据库会话。
        name: 平面类型名称。

    Returns:
        NetworkPlaneType 对象，不存在时返回 None。
    """
    return db.query(NetworkPlaneType).filter(NetworkPlaneType.name == name).first()


def count_regions_for_plane_type(db: Session, pt_id: str) -> int:
    """统计使用了指定网络平面类型的 Region 数量。

    Args:
        db: 数据库会话。
        pt_id: 平面类型 ID。

    Returns:
        Region 数量。
    """
    return db.query(func.count(RegionNetworkPlane.id)).filter(RegionNetworkPlane.plane_type_id == pt_id).scalar() or 0


def create_plane_type(db: Session, data: PlaneTypeCreate, operator: str) -> NetworkPlaneType:
    """创建网络平面类型。

    Args:
        db: 数据库会话。
        data: 创建参数。
        operator: 操作者名称。

    Returns:
        新创建的 NetworkPlaneType 对象。
    """
    pt = NetworkPlaneType(
        name=data.name,
        description=data.description or "",
        is_private=data.is_private,
        vrf=data.vrf or None,
    )
    db.add(pt)
    db.flush()
    log_change(
        db,
        entity_type="network_plane_type",
        entity_id=pt.id,
        action="create",
        operator=operator,
        new_value=pt.name,
    )
    return pt


def update_plane_type(db: Session, pt_id: str, data: PlaneTypeUpdate, operator: str) -> Optional[NetworkPlaneType]:
    """更新网络平面类型。

    Args:
        db: 数据库会话。
        pt_id: 要更新的平面类型 ID。
        data: 更新参数。
        operator: 操作者名称。

    Returns:
        更新后的 NetworkPlaneType 对象，不存在时返回 None。
    """
    pt = get_plane_type(db, pt_id)
    if not pt:
        return None
    changes = {}
    if data.name is not None and data.name != pt.name:
        changes["name"] = (pt.name, data.name)
        pt.name = data.name
    if data.description is not None and data.description != pt.description:
        changes["description"] = (pt.description or "", data.description or "")
        pt.description = data.description
    if data.is_private is not None and data.is_private != pt.is_private:
        changes["is_private"] = (pt.is_private, data.is_private)
        pt.is_private = data.is_private
    if "vrf" in data.model_fields_set:
        new_vrf = data.vrf or None
        if new_vrf != pt.vrf:
            changes["vrf"] = (pt.vrf or "", new_vrf or "")
            pt.vrf = new_vrf
    if changes:
        for field, (old, new) in changes.items():
            log_change(
                db,
                entity_type="network_plane_type",
                entity_id=pt_id,
                action="update",
                field_name=field,
                old_value=str(old),
                new_value=str(new),
                operator=operator,
            )
        db.flush()
    return pt


def delete_plane_type(db: Session, pt_id: str, operator: str) -> bool:
    """删除网络平面类型。

    如果该类型已被 Region 使用则拒绝删除。

    Args:
        db: 数据库会话。
        pt_id: 要删除的平面类型 ID。
        operator: 操作者名称。

    Returns:
        删除成功返回 True，不存在时返回 False。

    Raises:
        BusinessError: 平面类型正在被 Region 使用中。
    """
    pt = get_plane_type(db, pt_id)
    if not pt:
        return False
    region_count = count_regions_for_plane_type(db, pt_id)
    if region_count > 0:
        raise BusinessError(f"Cannot delete plane type in use by {region_count} region(s)")
    log_change(
        db,
        entity_type="network_plane_type",
        entity_id=pt_id,
        action="delete",
        operator=operator,
        old_value=pt.name,
    )
    db.delete(pt)
    db.flush()
    return True
