from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import ensure_region_business_write_allowed, get_current_user, operator_name
from app.exceptions import BusinessError
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.ip_allocation import AllocationCreate, AllocationResponse, AllocationUpdate
from app.schemas.lookup import LookupResponse, LookupResult
from app.services.allocation import (
    create_allocation,
    delete_allocation,
    get_allocation,
    list_allocations,
    update_allocation,
)
from app.services.lookup import lookup_allocations
from app.services.region import get_region
from app.utils.time_utils import format_datetime

router = APIRouter(tags=["Allocations"], dependencies=[Depends(get_current_user)])


@router.get("/api/regions/{region_id}/allocations", response_model=PaginatedResponse[AllocationResponse])
def list_allocations_endpoint(
    region_id: str,
    plane_type_id: Optional[str] = Query(None),
    plane_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> PaginatedResponse[AllocationResponse]:
    """查询 Region 下的 IP 分配列表。"""
    if not get_region(db, region_id):
        raise HTTPException(status_code=404, detail="Region not found")
    items, total = list_allocations(db, region_id, plane_type_id, plane_id, skip, limit)
    return PaginatedResponse(
        items=[AllocationResponse(**item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/api/regions/{region_id}/allocations", response_model=AllocationResponse, status_code=201)
def create_allocation_endpoint(
    region_id: str,
    data: AllocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AllocationResponse:
    """创建 IP 分配。"""
    if not get_region(db, region_id):
        raise HTTPException(status_code=404, detail="Region not found")
    ensure_region_business_write_allowed(current_user, region_id)
    try:
        allocation = create_allocation(db, region_id, data, operator_name(current_user))
    except BusinessError as e:
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    return AllocationResponse(
        **{
            "id": allocation.id,
            "region_id": allocation.region_id,
            "plane_type_id": allocation.plane_type_id,
            "region_name": allocation.region.name if allocation.region else "",
            "plane_type_name": allocation.plane_type.name if allocation.plane_type else "",
            "ip_range": allocation.ip_range,
            "vlan_id": allocation.vlan_id,
            "gateway": allocation.gateway or "",
            "subnet_mask": allocation.subnet_mask or "",
            "purpose": allocation.purpose or "",
            "status": allocation.status,
            "created_at": format_datetime(allocation.created_at),
            "updated_at": format_datetime(allocation.updated_at),
        }
    )


@router.get("/api/allocations/{allocation_id}", response_model=AllocationResponse)
def get_allocation_endpoint(allocation_id: str, db: Session = Depends(get_db)) -> AllocationResponse:
    """根据 ID 获取 IP 分配详情。"""
    a = get_allocation(db, allocation_id)
    if not a:
        raise HTTPException(status_code=404, detail="Allocation not found")
    return AllocationResponse(
        **{
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
            "created_at": format_datetime(a.created_at),
            "updated_at": format_datetime(a.updated_at),
        }
    )


@router.put("/api/allocations/{allocation_id}", response_model=AllocationResponse)
def update_allocation_endpoint(
    allocation_id: str,
    data: AllocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AllocationResponse:
    """更新 IP 分配信息。"""
    existing = get_allocation(db, allocation_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Allocation not found")
    ensure_region_business_write_allowed(current_user, existing.region_id)
    try:
        allocation = update_allocation(db, allocation_id, data, operator_name(current_user))
    except BusinessError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    db.commit()
    return AllocationResponse(
        **{
            "id": allocation.id,
            "region_id": allocation.region_id,
            "plane_type_id": allocation.plane_type_id,
            "region_name": allocation.region.name if allocation.region else "",
            "plane_type_name": allocation.plane_type.name if allocation.plane_type else "",
            "ip_range": allocation.ip_range,
            "vlan_id": allocation.vlan_id,
            "gateway": allocation.gateway or "",
            "subnet_mask": allocation.subnet_mask or "",
            "purpose": allocation.purpose or "",
            "status": allocation.status,
            "created_at": format_datetime(allocation.created_at),
            "updated_at": format_datetime(allocation.updated_at),
        }
    )


@router.delete("/api/allocations/{allocation_id}", status_code=204)
def delete_allocation_endpoint(
    allocation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """删除 IP 分配记录。"""
    allocation = get_allocation(db, allocation_id)
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    ensure_region_business_write_allowed(current_user, allocation.region_id)
    deleted = delete_allocation(db, allocation_id, operator_name(current_user))
    if not deleted:
        raise HTTPException(status_code=404, detail="Allocation not found")
    db.commit()


# Lookup endpoint
@router.get("/api/lookup", response_model=LookupResponse)
def lookup_endpoint(
    q: str = Query(..., min_length=1),
    exact: bool = Query(True),
    db: Session = Depends(get_db),
) -> LookupResponse:
    """按 IP 或 CIDR 查询分配记录。"""
    try:
        results = lookup_allocations(db, q, exact)
    except BusinessError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return LookupResponse(
        results=[
            LookupResult(
                id=a.id,
                ip_range=a.ip_range,
                region_name=a.region.name if a.region else "",
                plane_type_name=a.plane_type.name if a.plane_type else "",
                vlan_id=a.vlan_id,
                gateway=a.gateway,
                subnet_mask=a.subnet_mask,
                purpose=a.purpose,
                status=a.status,
            )
            for a in results
        ],
        total=len(results),
    )
