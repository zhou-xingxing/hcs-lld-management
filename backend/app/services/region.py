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


def get_region_detail(db: Session, region_id: str) -> Optional[dict]:
    """获取 Region 详情，planes 返回树形结构。"""
    from app.services.region_plane import get_region_plane_tree

    region = get_region(db, region_id)
    if not region:
        return None
    plane_tree = get_region_plane_tree(db, region_id)

    # 计算平面总数（扁平化树）
    def _count_planes(nodes: list[dict]) -> int:
        count = 0
        for n in nodes:
            count += 1 + _count_planes(n.get("children", []))
        return count

    return {
        "id": region.id,
        "name": region.name,
        "description": region.description or "",
        "plane_count": _count_planes(plane_tree),
        "allocation_count": (
            db.query(func.count(IPAllocation.id))
            .filter(IPAllocation.region_id == region_id)
            .scalar()
            or 0
        ),
        "planes": plane_tree,
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
