from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
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
from app.services.region import get_region
from app.utils.ip_utils import find_containing_networks, find_overlapping, parse_cidr, parse_ip

router = APIRouter(tags=["Allocations"])


def get_operator(x_operator: str = Header("system")) -> str:
    return x_operator


@router.get("/api/regions/{region_id}/allocations", response_model=PaginatedResponse[AllocationResponse])
def list_allocations_endpoint(
    region_id: str,
    plane_type_id: Optional[str] = Query(None),
    plane_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
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
    operator: str = Depends(get_operator),
):
    if not get_region(db, region_id):
        raise HTTPException(status_code=404, detail="Region not found")
    try:
        allocation = create_allocation(db, region_id, data, operator)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    db.commit()
    return AllocationResponse(**{
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
        "created_at": allocation.created_at.isoformat(),
        "updated_at": allocation.updated_at.isoformat(),
    })


@router.get("/api/allocations/{allocation_id}", response_model=AllocationResponse)
def get_allocation_endpoint(allocation_id: str, db: Session = Depends(get_db)):
    a = get_allocation(db, allocation_id)
    if not a:
        raise HTTPException(status_code=404, detail="Allocation not found")
    return AllocationResponse(**{
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
    })


@router.put("/api/allocations/{allocation_id}", response_model=AllocationResponse)
def update_allocation_endpoint(
    allocation_id: str,
    data: AllocationUpdate,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
):
    try:
        allocation = update_allocation(db, allocation_id, data, operator)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    db.commit()
    return AllocationResponse(**{
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
        "created_at": allocation.created_at.isoformat(),
        "updated_at": allocation.updated_at.isoformat(),
    })


@router.delete("/api/allocations/{allocation_id}", status_code=204)
def delete_allocation_endpoint(
    allocation_id: str,
    db: Session = Depends(get_db),
    operator: str = Depends(get_operator),
):
    deleted = delete_allocation(db, allocation_id, operator)
    if not deleted:
        raise HTTPException(status_code=404, detail="Allocation not found")
    db.commit()


# Lookup endpoint
@router.get("/api/lookup", response_model=LookupResponse)
def lookup_endpoint(
    q: str = Query(..., min_length=1),
    exact: bool = Query(True),
    db: Session = Depends(get_db),
):
    from app.models.ip_allocation import IPAllocation

    allocations = db.query(IPAllocation).all()
    results = []

    # Try single IP first, then CIDR (to avoid parse_cidr treating "10.0.0.5" as /32)
    ip = parse_ip(q)
    net = parse_cidr(q) if not ip else None

    if ip:
        # Single IP lookup - find containing networks
        for a in allocations:
            existing = parse_cidr(a.ip_range)
            if existing and ip in existing:
                results.append(a)
    elif net:
        # CIDR lookup
        if exact:
            # Exact CIDR match
            for a in allocations:
                existing = parse_cidr(a.ip_range)
                if existing and existing == net:
                    results.append(a)
        else:
            # Overlap lookup
            for a in allocations:
                existing = parse_cidr(a.ip_range)
                if existing and existing.overlaps(net):
                    results.append(a)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid IP address or CIDR: {q}")

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
