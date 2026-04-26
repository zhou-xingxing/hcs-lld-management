from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import BusinessError
from app.schemas.common import PaginatedResponse
from app.schemas.network_plane_type import PlaneTypeCreate, PlaneTypeResponse, PlaneTypeUpdate
from app.services.network_plane_type import (
    count_regions_for_plane_type,
    create_plane_type,
    delete_plane_type,
    get_plane_type,
    list_plane_types,
    update_plane_type,
)
from app.utils.time_utils import format_datetime

router = APIRouter(prefix="/api/network-plane-types", tags=["Network Plane Types"])


def get_operator(x_operator: str = Header("system")) -> str:
    return x_operator


@router.get("", response_model=PaginatedResponse[PlaneTypeResponse])
def list_plane_types_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> PaginatedResponse[PlaneTypeResponse]:
    """查询网络平面类型列表。"""
    items, total = list_plane_types(db, skip=skip, limit=limit)
    result = []
    for pt in items:
        result.append(
            PlaneTypeResponse(
                id=pt.id,
                name=pt.name,
                description=pt.description or "",
                region_count=count_regions_for_plane_type(db, pt.id),
                created_at=format_datetime(pt.created_at),
            )
        )
    return PaginatedResponse(items=result, total=total, skip=skip, limit=limit)


@router.post("", response_model=PlaneTypeResponse, status_code=201)
def create_plane_type_endpoint(
    data: PlaneTypeCreate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
) -> PlaneTypeResponse:
    """创建网络平面类型。"""
    pt = create_plane_type(db, data, operator)
    db.commit()
    return PlaneTypeResponse(
        id=pt.id,
        name=pt.name,
        description=pt.description or "",
        region_count=0,
        created_at=format_datetime(pt.created_at),
    )


@router.get("/{pt_id}", response_model=PlaneTypeResponse)
def get_plane_type_endpoint(pt_id: str, db: Session = Depends(get_db)) -> PlaneTypeResponse:
    """根据 ID 获取网络平面类型详情。"""
    pt = get_plane_type(db, pt_id)
    if not pt:
        raise HTTPException(status_code=404, detail="Plane type not found")
    return PlaneTypeResponse(
        id=pt.id,
        name=pt.name,
        description=pt.description or "",
        region_count=count_regions_for_plane_type(db, pt_id),
        created_at=format_datetime(pt.created_at),
    )


@router.put("/{pt_id}", response_model=PlaneTypeResponse)
def update_plane_type_endpoint(
    pt_id: str,
    data: PlaneTypeUpdate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
) -> PlaneTypeResponse:
    """更新网络平面类型。"""
    pt = update_plane_type(db, pt_id, data, operator)
    if not pt:
        raise HTTPException(status_code=404, detail="Plane type not found")
    db.commit()
    return PlaneTypeResponse(
        id=pt.id,
        name=pt.name,
        description=pt.description or "",
        region_count=count_regions_for_plane_type(db, pt_id),
        created_at=format_datetime(pt.created_at),
    )


@router.delete("/{pt_id}", status_code=204)
def delete_plane_type_endpoint(
    pt_id: str,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
) -> None:
    """删除网络平面类型。"""
    try:
        deleted = delete_plane_type(db, pt_id, operator)
    except BusinessError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Plane type not found")
    db.commit()
