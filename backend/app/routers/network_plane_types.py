from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import PaginatedResponse, MessageResponse
from app.schemas.network_plane_type import PlaneTypeCreate, PlaneTypeResponse, PlaneTypeUpdate
from app.services.network_plane_type import (
    count_regions_for_plane_type,
    create_plane_type,
    delete_plane_type,
    get_plane_type,
    list_plane_types,
    update_plane_type,
)

router = APIRouter(prefix="/api/network-plane-types", tags=["Network Plane Types"])


def get_operator(x_operator: str = Header("system")) -> str:
    return x_operator


@router.get("", response_model=PaginatedResponse[PlaneTypeResponse])
def list_plane_types_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    items, total = list_plane_types(db, skip=skip, limit=limit)
    result = []
    for pt in items:
        result.append(
            PlaneTypeResponse(
                id=pt.id,
                name=pt.name,
                description=pt.description or "",
                region_count=count_regions_for_plane_type(db, pt.id),
                created_at=pt.created_at.isoformat(),
            )
        )
    return PaginatedResponse(items=result, total=total, skip=skip, limit=limit)


@router.post("", response_model=PlaneTypeResponse, status_code=201)
def create_plane_type_endpoint(
    data: PlaneTypeCreate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
):
    pt = create_plane_type(db, data, operator)
    db.commit()
    return PlaneTypeResponse(
        id=pt.id,
        name=pt.name,
        description=pt.description or "",
        region_count=0,
        created_at=pt.created_at.isoformat(),
    )


@router.get("/{pt_id}", response_model=PlaneTypeResponse)
def get_plane_type_endpoint(pt_id: str, db: Session = Depends(get_db)):
    pt = get_plane_type(db, pt_id)
    if not pt:
        raise HTTPException(status_code=404, detail="Plane type not found")
    return PlaneTypeResponse(
        id=pt.id,
        name=pt.name,
        description=pt.description or "",
        region_count=count_regions_for_plane_type(db, pt_id),
        created_at=pt.created_at.isoformat(),
    )


@router.put("/{pt_id}", response_model=PlaneTypeResponse)
def update_plane_type_endpoint(
    pt_id: str,
    data: PlaneTypeUpdate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
):
    pt = update_plane_type(db, pt_id, data, operator)
    if not pt:
        raise HTTPException(status_code=404, detail="Plane type not found")
    db.commit()
    return PlaneTypeResponse(
        id=pt.id,
        name=pt.name,
        description=pt.description or "",
        region_count=count_regions_for_plane_type(db, pt_id),
        created_at=pt.created_at.isoformat(),
    )


@router.delete("/{pt_id}", status_code=204)
def delete_plane_type_endpoint(
    pt_id: str,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
):
    try:
        deleted = delete_plane_type(db, pt_id, operator)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Plane type not found")
    db.commit()
