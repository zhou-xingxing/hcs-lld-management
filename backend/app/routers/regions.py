from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.region import (
    RegionCreate,
    RegionDetailResponse,
    RegionPlaneCreate,
    RegionResponse,
    RegionUpdate,
)
from app.schemas.common import PaginatedResponse
from app.services.region import (
    create_region,
    delete_region,
    get_region_detail,
    list_regions,
    update_region,
)
from app.services.region_plane import (
    disable_plane_for_region,
    enable_plane_for_region,
    get_region_planes,
)

router = APIRouter(prefix="/api/regions", tags=["Regions"])


def get_operator(x_operator: str = Header("system")) -> str:
    return x_operator


@router.get("", response_model=PaginatedResponse[RegionResponse])
def list_regions_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    regions, total = list_regions(db, skip=skip, limit=limit, search=search)
    items = []
    for r in regions:
        items.append(
            RegionResponse(
                id=r.id,
                name=r.name,
                description=r.description or "",
                plane_count=len(r.region_planes) if r.region_planes else 0,
                allocation_count=len(r.allocations) if r.allocations else 0,
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat(),
            )
        )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=RegionResponse, status_code=201)
def create_region_endpoint(
    data: RegionCreate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
):
    try:
        region = create_region(db, data, operator)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    return RegionResponse(
        id=region.id,
        name=region.name,
        description=region.description or "",
        plane_count=0,
        allocation_count=0,
        created_at=region.created_at.isoformat(),
        updated_at=region.updated_at.isoformat(),
    )


@router.get("/{region_id}", response_model=RegionDetailResponse)
def get_region_endpoint(region_id: str, db: Session = Depends(get_db)):
    detail = get_region_detail(db, region_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Region not found")
    return RegionDetailResponse(**detail)


@router.put("/{region_id}", response_model=RegionResponse)
def update_region_endpoint(
    region_id: str,
    data: RegionUpdate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
):
    region = update_region(db, region_id, data, operator)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    db.commit()
    return RegionResponse(
        id=region.id,
        name=region.name,
        description=region.description or "",
        plane_count=len(region.region_planes) if region.region_planes else 0,
        allocation_count=len(region.allocations) if region.allocations else 0,
        created_at=region.created_at.isoformat(),
        updated_at=region.updated_at.isoformat(),
    )


@router.delete("/{region_id}", status_code=204)
def delete_region_endpoint(
    region_id: str,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
):
    deleted = delete_region(db, region_id, operator)
    if not deleted:
        raise HTTPException(status_code=404, detail="Region not found")
    db.commit()


# Region-Plan association endpoints
@router.get("/{region_id}/planes")
def list_region_planes_endpoint(region_id: str, db: Session = Depends(get_db)):
    from app.services.region import get_region

    region = get_region(db, region_id)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return get_region_planes(db, region_id)


@router.post("/{region_id}/planes", status_code=201)
def enable_plane_endpoint(
    region_id: str,
    data: RegionPlaneCreate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
):
    from app.models.network_plane_type import NetworkPlaneType
    from app.services.region import get_region

    region = get_region(db, region_id)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    pt = db.query(NetworkPlaneType).filter(NetworkPlaneType.id == data.plane_type_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Plane type not found")
    rp = enable_plane_for_region(db, region_id, data.plane_type_id, operator)
    db.commit()
    return {
        "id": rp.id,
        "region_id": rp.region_id,
        "plane_type_id": rp.plane_type_id,
        "plane_type_name": pt.name,
    }


@router.delete("/{region_id}/planes/{plane_id}", status_code=204)
def disable_plane_endpoint(
    region_id: str,
    plane_id: str,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
):
    deleted = disable_plane_for_region(db, region_id, plane_id, operator)
    if not deleted:
        raise HTTPException(status_code=404, detail="Region plane association not found")
    db.commit()
