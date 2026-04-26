from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import BusinessError
from app.schemas.common import PaginatedResponse
from app.schemas.region import (
    ChildPlaneCreate,
    RegionCreate,
    RegionDetailResponse,
    RegionPlaneCreate,
    RegionResponse,
    RegionUpdate,
)
from app.services.region import (
    create_region,
    delete_region,
    get_region_detail,
    list_regions,
    update_region,
)
from app.services.region_plane import (
    create_child_plane,
    disable_plane_for_region,
    enable_plane_for_region,
    get_region_plane_tree,
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
) -> PaginatedResponse[RegionResponse]:
    """查询 Region 列表。"""
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
) -> RegionResponse:
    """创建新 Region。"""
    try:
        region = create_region(db, data, operator)
    except BusinessError as e:
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
def get_region_endpoint(region_id: str, db: Session = Depends(get_db)) -> RegionDetailResponse:
    """获取 Region 详情（含网络平面树形结构）。"""
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
) -> RegionResponse:
    """更新 Region 信息。"""
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
) -> None:
    """删除 Region。"""
    deleted = delete_region(db, region_id, operator)
    if not deleted:
        raise HTTPException(status_code=404, detail="Region not found")
    db.commit()


# Region-Plan association endpoints
@router.get("/{region_id}/planes")
def list_region_planes_endpoint(region_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """查询 Region 下所有网络平面的树形结构。"""
    from app.services.region import get_region

    region = get_region(db, region_id)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return get_region_plane_tree(db, region_id)


@router.post("/{region_id}/planes", status_code=201)
def enable_plane_endpoint(
    region_id: str,
    data: RegionPlaneCreate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
) -> dict[str, Any]:
    """为 Region 启用根级网络平面。"""
    from app.models.network_plane_type import NetworkPlaneType
    from app.services.region import get_region

    region = get_region(db, region_id)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    pt = db.query(NetworkPlaneType).filter(NetworkPlaneType.id == data.plane_type_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="Plane type not found")
    try:
        rp = enable_plane_for_region(db, region_id, data.plane_type_id, data.cidr, operator)
    except BusinessError as e:
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    return {
        "id": rp.id,
        "region_id": rp.region_id,
        "plane_type_id": rp.plane_type_id,
        "plane_type_name": pt.name,
        "cidr": rp.cidr,
        "parent_id": rp.parent_id,
        "children": [],
    }


@router.post("/{region_id}/planes/{plane_id}/children", status_code=201)
def create_child_plane_endpoint(
    region_id: str,
    plane_id: str,
    data: ChildPlaneCreate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
) -> dict[str, Any]:
    """在指定父平面下创建子网络平面（最多 3 级嵌套）。"""
    from app.services.region import get_region

    region = get_region(db, region_id)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    try:
        child = create_child_plane(db, region_id, plane_id, data.cidr, operator)
    except BusinessError as e:
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    return {
        "id": child.id,
        "region_id": child.region_id,
        "plane_type_id": child.plane_type_id,
        "cidr": child.cidr,
        "parent_id": child.parent_id,
        "children": [],
    }


@router.delete("/{region_id}/planes/{plane_id}", status_code=204)
def disable_plane_endpoint(
    region_id: str,
    plane_id: str,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
) -> None:
    """删除平面节点（级联删除子平面及 IP 分配）。"""
    deleted = disable_plane_for_region(db, region_id, plane_id, operator)
    if not deleted:
        raise HTTPException(status_code=404, detail="Region plane association not found")
    db.commit()
