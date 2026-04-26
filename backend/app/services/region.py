from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ip_allocation import IPAllocation
from app.models.region import Region
from app.models.region_network_plane import RegionNetworkPlane
from app.schemas.region import RegionCreate, RegionUpdate
from app.services.change_log import log_change


def list_regions(
    db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None
) -> tuple[list[Region], int]:
    query = db.query(Region)
    if search:
        query = query.filter(Region.name.ilike(f"%{search}%"))
    total = query.count()
    regions = query.order_by(Region.created_at.desc()).offset(skip).limit(limit).all()
    return regions, total


def get_region(db: Session, region_id: str) -> Optional[Region]:
    return db.query(Region).filter(Region.id == region_id).first()


def _get_plane_allocation_count(db: Session, region_id: str, plane_type_id: str) -> int:
    return (
        db.query(func.count(IPAllocation.id))
        .filter(
            IPAllocation.region_id == region_id,
            IPAllocation.plane_type_id == plane_type_id,
        )
        .scalar()
        or 0
    )


def get_region_detail(db: Session, region_id: str) -> Optional[dict]:
    region = get_region(db, region_id)
    if not region:
        return None
    planes = (
        db.query(RegionNetworkPlane)
        .filter(RegionNetworkPlane.region_id == region_id)
        .all()
    )
    plane_list = []
    for rp in planes:
        plane_list.append(
            {
                "id": rp.id,
                "region_id": rp.region_id,
                "plane_type_id": rp.plane_type_id,
                "plane_type_name": rp.plane_type.name if rp.plane_type else "",
                "allocation_count": _get_plane_allocation_count(
                    db, region_id, rp.plane_type_id
                ),
            }
        )
    return {
        "id": region.id,
        "name": region.name,
        "description": region.description or "",
        "plane_count": len(plane_list),
        "allocation_count": (
            db.query(func.count(IPAllocation.id))
            .filter(IPAllocation.region_id == region_id)
            .scalar()
            or 0
        ),
        "planes": plane_list,
        "created_at": region.created_at.isoformat(),
        "updated_at": region.updated_at.isoformat(),
    }


def create_region(db: Session, data: RegionCreate, operator: str) -> Region:
    # Check for duplicate name
    existing = db.query(Region).filter(Region.name == data.name).first()
    if existing:
        raise ValueError(f"Region with name '{data.name}' already exists")

    region = Region(name=data.name, description=data.description or "")
    db.add(region)
    db.flush()
    log_change(
        db,
        entity_type="region",
        entity_id=region.id,
        action="create",
        operator=operator,
        new_value=region.name,
    )
    return region


def update_region(db: Session, region_id: str, data: RegionUpdate, operator: str) -> Optional[Region]:
    region = get_region(db, region_id)
    if not region:
        return None
    changes = {}
    if data.name is not None and data.name != region.name:
        changes["name"] = (region.name, data.name)
        region.name = data.name
    if data.description is not None and data.description != region.description:
        changes["description"] = (region.description or "", data.description or "")
        region.description = data.description
    if changes:
        for field, (old, new) in changes.items():
            log_change(
                db,
                entity_type="region",
                entity_id=region_id,
                action="update",
                field_name=field,
                old_value=str(old),
                new_value=str(new),
                operator=operator,
            )
        db.flush()
    return region


def delete_region(db: Session, region_id: str, operator: str) -> bool:
    region = get_region(db, region_id)
    if not region:
        return False
    log_change(
        db,
        entity_type="region",
        entity_id=region_id,
        action="delete",
        operator=operator,
        old_value=region.name,
    )
    db.delete(region)
    db.flush()
    return True
