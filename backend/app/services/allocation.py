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
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[dict], int]:
    query = db.query(IPAllocation).filter(IPAllocation.region_id == region_id)
    if plane_type_id:
        query = query.filter(IPAllocation.plane_type_id == plane_type_id)
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


def _get_allocated_cidrs(db: Session, region_id: str, plane_type_id: str) -> list[str]:
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
    # Validate CIDR
    net = parse_cidr(data.ip_range)
    if not net:
        raise ValueError(f"Invalid CIDR notation: {data.ip_range}")

    # Validate plane belongs to region
    if not _validate_plane_association(db, region_id, data.plane_type_id):
        raise ValueError("Plane type is not enabled for this region")

    # Check overlap
    existing = _get_allocated_cidrs(db, region_id, data.plane_type_id)
    overlapped = find_overlapping(data.ip_range, existing)
    if overlapped:
        raise ValueError(f"IP range overlaps with existing allocations: {', '.join(overlapped)}")

    allocation = IPAllocation(
        region_id=region_id,
        plane_type_id=data.plane_type_id,
        ip_range=data.ip_range,
        vlan_id=data.vlan_id,
        gateway=data.gateway,
        subnet_mask=data.subnet_mask,
        purpose=data.purpose or "",
        status=data.status or "active",
    )
    db.add(allocation)
    db.flush()

    # Get plane type name for log
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
            "vlan_id": data.vlan_id,
            "status": data.status,
        }),
    )
    return allocation


def update_allocation(
    db: Session, allocation_id: str, data: AllocationUpdate, operator: str
) -> Optional[IPAllocation]:
    allocation = get_allocation(db, allocation_id)
    if not allocation:
        return None

    changes = []
    if data.ip_range is not None and data.ip_range != allocation.ip_range:
        net = parse_cidr(data.ip_range)
        if not net:
            raise ValueError(f"Invalid CIDR notation: {data.ip_range}")
        # Check overlap with other allocations in same region+plane
        existing = _get_allocated_cidrs(db, allocation.region_id, allocation.plane_type_id)
        existing = [e for e in existing if e != allocation.ip_range]
        overlapped = find_overlapping(data.ip_range, existing)
        if overlapped:
            raise ValueError(f"IP range overlaps with: {', '.join(overlapped)}")
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
        }),
    )
    db.delete(allocation)
    db.flush()
    return True
