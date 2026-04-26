from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.region_network_plane import RegionNetworkPlane
from app.models.network_plane_type import NetworkPlaneType
from app.services.change_log import log_change


def get_region_planes(db: Session, region_id: str) -> list[dict]:
    items = (
        db.query(RegionNetworkPlane)
        .filter(RegionNetworkPlane.region_id == region_id)
        .all()
    )
    result = []
    for rp in items:
        result.append(
            {
                "id": rp.id,
                "region_id": rp.region_id,
                "plane_type_id": rp.plane_type_id,
                "plane_type_name": rp.plane_type.name if rp.plane_type else "",
            }
        )
    return result


def enable_plane_for_region(
    db: Session, region_id: str, plane_type_id: str, operator: str
) -> Optional[RegionNetworkPlane]:
    existing = (
        db.query(RegionNetworkPlane)
        .filter(
            RegionNetworkPlane.region_id == region_id,
            RegionNetworkPlane.plane_type_id == plane_type_id,
        )
        .first()
    )
    if existing:
        return existing
    rp = RegionNetworkPlane(region_id=region_id, plane_type_id=plane_type_id)
    db.add(rp)
    db.flush()
    pt = db.query(NetworkPlaneType).filter(NetworkPlaneType.id == plane_type_id).first()
    log_change(
        db,
        entity_type="region_network_plane",
        entity_id=rp.id,
        action="create",
        operator=operator,
        new_value=f"region={region_id}, plane_type={pt.name if pt else plane_type_id}",
    )
    return rp


def disable_plane_for_region(
    db: Session, region_id: str, plane_id: str, operator: str
) -> bool:
    rp = (
        db.query(RegionNetworkPlane)
        .filter(
            RegionNetworkPlane.id == plane_id,
            RegionNetworkPlane.region_id == region_id,
        )
        .first()
    )
    if not rp:
        return False
    pt_name = rp.plane_type.name if rp.plane_type else "unknown"
    log_change(
        db,
        entity_type="region_network_plane",
        entity_id=plane_id,
        action="delete",
        operator=operator,
        old_value=f"region={region_id}, plane_type={pt_name}",
    )
    db.delete(rp)
    db.flush()
    return True
