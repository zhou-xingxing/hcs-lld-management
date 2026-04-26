from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.region_network_plane import RegionNetworkPlane
from app.models.network_plane_type import NetworkPlaneType
from app.schemas.network_plane_type import PlaneTypeCreate, PlaneTypeUpdate
from app.services.change_log import log_change


def list_plane_types(
    db: Session, skip: int = 0, limit: int = 100
) -> tuple[list[NetworkPlaneType], int]:
    total = db.query(NetworkPlaneType).count()
    items = db.query(NetworkPlaneType).order_by(NetworkPlaneType.created_at.asc()).offset(skip).limit(limit).all()
    return items, total


def get_plane_type(db: Session, pt_id: str) -> Optional[NetworkPlaneType]:
    return db.query(NetworkPlaneType).filter(NetworkPlaneType.id == pt_id).first()


def get_plane_type_by_name(db: Session, name: str) -> Optional[NetworkPlaneType]:
    return db.query(NetworkPlaneType).filter(NetworkPlaneType.name == name).first()


def count_regions_for_plane_type(db: Session, pt_id: str) -> int:
    return (
        db.query(func.count(RegionNetworkPlane.id))
        .filter(RegionNetworkPlane.plane_type_id == pt_id)
        .scalar()
        or 0
    )


def create_plane_type(db: Session, data: PlaneTypeCreate, operator: str) -> NetworkPlaneType:
    pt = NetworkPlaneType(name=data.name, description=data.description or "")
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


def update_plane_type(
    db: Session, pt_id: str, data: PlaneTypeUpdate, operator: str
) -> Optional[NetworkPlaneType]:
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
    pt = get_plane_type(db, pt_id)
    if not pt:
        return False
    region_count = count_regions_for_plane_type(db, pt_id)
    if region_count > 0:
        raise ValueError(f"Cannot delete plane type in use by {region_count} region(s)")
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
