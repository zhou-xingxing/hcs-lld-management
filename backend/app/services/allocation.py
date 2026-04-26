from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ip_allocation import IPAllocation
from app.models.network_plane_type import NetworkPlaneType
from app.models.region_network_plane import RegionNetworkPlane
from app.schemas.ip_allocation import AllocationCreate, AllocationUpdate
from app.services.change_log import log_change
from app.utils.ip_utils import find_overlapping, parse_cidr


def list_allocations(
    db: Session,
    region_id: str,
    plane_type_id: Optional[str] = None,
    plane_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[dict], int]:
    query = db.query(IPAllocation).filter(IPAllocation.region_id == region_id)
    if plane_type_id:
        query = query.filter(IPAllocation.plane_type_id == plane_type_id)
    if plane_id:
        query = query.filter(IPAllocation.plane_id == plane_id)
    total = query.count()
    items = query.order_by(IPAllocation.created_at.desc()).offset(skip).limit(limit).all()
    result = []
    for a in items:
        result.append(_allocation_to_dict(a))
    return result, total


def get_allocation(db: Session, allocation_id: str) -> Optional[IPAllocation]:
    return db.query(IPAllocation).filter(IPAllocation.id == allocation_id).first()


def _allocation_to_dict(a: IPAllocation) -> dict:
    return {
        "id": a.id,
        "region_id": a.region_id,
        "plane_type_id": a.plane_type_id,
        "plane_id": a.plane_id,
        "region_name": a.region.name if a.region else "",
        "plane_type_name": a.plane_type.name if a.plane_type else "",
        "ip_range": a.ip_range,
        "vlan_id": a.vlan_id,
        "gateway": a.gateway or "",
        "subnet_mask": a.subnet_mask or "",
        "purpose": a.purpose or "",
        "status": a.status,
        "created_at": a.created_at.isoformat(),
        "updated_at": a.updated_at.isoformat(),
    }


def _get_allocated_cidrs_in_plane(db: Session, plane_id: str) -> list[str]:
    """查询指定平面节点下已有的 IP 分配 CIDR 列表。"""
    results = (
        db.query(IPAllocation.ip_range)
        .filter(IPAllocation.plane_id == plane_id)
        .all()
    )
    return [r[0] for r in results]


def _get_child_plane_cidrs(db: Session, plane_id: str) -> list[str]:
    """查询指定平面的直接子平面 CIDR 列表。"""
    children = (
        db.query(RegionNetworkPlane.cidr)
        .filter(RegionNetworkPlane.parent_id == plane_id)
        .all()
    )
    return [c[0] for c in children if c[0]]


def _get_legacy_allocated_cidrs(db: Session, region_id: str, plane_type_id: str) -> list[str]:
    """[兼容] 按 (region_id, plane_type_id) 查询已有 CIDR，用于无 plane_id 的旧数据。"""
    results = (
        db.query(IPAllocation.ip_range)
        .filter(
            IPAllocation.region_id == region_id,
            IPAllocation.plane_type_id == plane_type_id,
        )
        .all()
    )
    return [r[0] for r in results]


def _validate_plane_association(db: Session, region_id: str, plane_type_id: str) -> bool:
    """校验 plane_type 是否已在 Region 中启用（兼容旧数据，按 plane_type_id 检查）。"""
    return (
        db.query(RegionNetworkPlane)
        .filter(
            RegionNetworkPlane.region_id == region_id,
            RegionNetworkPlane.plane_type_id == plane_type_id,
        )
        .first()
        is not None
    )


def create_allocation(
    db: Session, region_id: str, data: AllocationCreate, operator: str
) -> IPAllocation:
    """创建 IP 分配，校验 CIDR 约束：在平面 CIDR 范围内、不与子平面 CIDR 重叠、同平面内不重叠。"""
    # 校验 CIDR 格式
    net = parse_cidr(data.ip_range)
    if not net:
        raise ValueError(f"无效的 CIDR 格式: {data.ip_range}")

    # 校验：plane 存在且属于该 Region
    plane = db.query(RegionNetworkPlane).filter(
        RegionNetworkPlane.id == data.plane_id,
        RegionNetworkPlane.region_id == region_id,
        RegionNetworkPlane.plane_type_id == data.plane_type_id,
    ).first()
    if not plane:
        raise ValueError("网络平面不存在或未在该 Region 启用")
    if not plane.cidr:
        raise ValueError("该网络平面没有 CIDR 范围，无法创建 IP 分配")

    # 校验：IP 段必须在平面 CIDR 范围内
    plane_net = parse_cidr(plane.cidr)
    if plane_net:
        subnet_check = (
            net.subnet_of(plane_net)
            if hasattr(net, "subnet_of")
            else plane_net.supernet_of(net)
        )
        if not subnet_check:
            raise ValueError(f"IP 段 {data.ip_range} 超出平面 CIDR {plane.cidr} 范围")

    # 校验：IP 段不能与子平面的 CIDR 重叠（子平面已占用了子网段）
    child_cidrs = _get_child_plane_cidrs(db, plane.id)
    overlapped = find_overlapping(data.ip_range, child_cidrs)
    if overlapped:
        raise ValueError(f"IP 段与子网平面 CIDR 重叠: {', '.join(overlapped)}")

    # 校验：同平面内 IP 段不重叠
    existing = _get_allocated_cidrs_in_plane(db, plane.id)
    overlapped = find_overlapping(data.ip_range, existing)
    if overlapped:
        raise ValueError(f"与同平面的已有 IP 分配重叠: {', '.join(overlapped)}")

    allocation = IPAllocation(
        region_id=region_id,
        plane_type_id=data.plane_type_id,
        plane_id=data.plane_id,
        ip_range=data.ip_range,
        vlan_id=data.vlan_id,
        gateway=data.gateway,
        subnet_mask=data.subnet_mask,
        purpose=data.purpose or "",
        status=data.status or "active",
    )
    db.add(allocation)
    db.flush()

    pt = db.query(NetworkPlaneType).filter(NetworkPlaneType.id == data.plane_type_id).first()
    log_change(
        db,
        entity_type="ip_allocation",
        entity_id=allocation.id,
        action="create",
        operator=operator,
        new_value=json.dumps({
            "ip_range": data.ip_range,
            "region_id": region_id,
            "plane_type": pt.name if pt else data.plane_type_id,
            "plane_id": data.plane_id,
            "vlan_id": data.vlan_id,
            "status": data.status,
        }),
    )
    return allocation


def update_allocation(
    db: Session, allocation_id: str, data: AllocationUpdate, operator: str
) -> Optional[IPAllocation]:
    """更新 IP 分配，如果修改了 ip_range 则重新校验 CIDR 约束。"""
    allocation = get_allocation(db, allocation_id)
    if not allocation:
        return None

    changes = []
    if data.ip_range is not None and data.ip_range != allocation.ip_range:
        net = parse_cidr(data.ip_range)
        if not net:
            raise ValueError(f"无效的 CIDR 格式: {data.ip_range}")

        # 如果有 plane_id，按新逻辑校验
        if allocation.plane_id:
            plane = db.get(RegionNetworkPlane, allocation.plane_id)
            if plane and plane.cidr:
                plane_net = parse_cidr(plane.cidr)
                if plane_net:
                    subnet_check = (
                        net.subnet_of(plane_net)
                        if hasattr(net, "subnet_of")
                        else plane_net.supernet_of(net)
                    )
                    if not subnet_check:
                        raise ValueError(f"IP 段 {data.ip_range} 超出平面 CIDR {plane.cidr} 范围")

            # 不与子平面 CIDR 重叠
            child_cidrs = _get_child_plane_cidrs(db, allocation.plane_id)
            overlapped = find_overlapping(data.ip_range, child_cidrs)
            if overlapped:
                raise ValueError(f"IP 段与子网平面 CIDR 重叠: {', '.join(overlapped)}")

            # 同平面内不重叠（排除自身）
            existing = _get_allocated_cidrs_in_plane(db, allocation.plane_id)
            existing = [e for e in existing if e != allocation.ip_range]
            overlapped = find_overlapping(data.ip_range, existing)
            if overlapped:
                raise ValueError(f"与同平面的已有 IP 分配重叠: {', '.join(overlapped)}")
        else:
            # 旧数据无 plane_id，回退到按 (region_id, plane_type_id) 扫描
            existing = _get_legacy_allocated_cidrs(db, allocation.region_id, allocation.plane_type_id)
            existing = [e for e in existing if e != allocation.ip_range]
            overlapped = find_overlapping(data.ip_range, existing)
            if overlapped:
                raise ValueError(f"IP 段与已有分配重叠: {', '.join(overlapped)}")

        changes.append(("ip_range", allocation.ip_range, data.ip_range))
        allocation.ip_range = data.ip_range

    for field in ["vlan_id", "gateway", "subnet_mask", "purpose", "status"]:
        new_val = getattr(data, field, None)
        if new_val is not None:
            old_val = getattr(allocation, field)
            if str(new_val) != str(old_val):
                changes.append((field, str(old_val or ""), str(new_val)))
                setattr(allocation, field, new_val)

    if changes:
        for field, old, new in changes:
            log_change(
                db,
                entity_type="ip_allocation",
                entity_id=allocation_id,
                action="update",
                field_name=field,
                old_value=str(old),
                new_value=str(new),
                operator=operator,
            )
        db.flush()
    return allocation


def delete_allocation(db: Session, allocation_id: str, operator: str) -> bool:
    allocation = get_allocation(db, allocation_id)
    if not allocation:
        return False
    log_change(
        db,
        entity_type="ip_allocation",
        entity_id=allocation_id,
        action="delete",
        operator=operator,
        old_value=json.dumps({
            "ip_range": allocation.ip_range,
            "region_id": allocation.region_id,
            "plane_type_id": allocation.plane_type_id,
            "plane_id": allocation.plane_id,
        }),
    )
    db.delete(allocation)
    db.flush()
    return True
