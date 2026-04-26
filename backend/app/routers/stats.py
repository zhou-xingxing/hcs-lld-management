from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.change_log import ChangeLog
from app.models.ip_allocation import IPAllocation
from app.models.network_plane_type import NetworkPlaneType
from app.models.region import Region

router = APIRouter(prefix="/api/stats", tags=["Stats"])


@router.get("")
def get_stats(db: Session = Depends(get_db)):
    total_regions = db.query(func.count(Region.id)).scalar() or 0
    total_plane_types = db.query(func.count(NetworkPlaneType.id)).scalar() or 0
    total_allocations = db.query(func.count(IPAllocation.id)).scalar() or 0
    total_change_logs = db.query(func.count(ChangeLog.id)).scalar() or 0

    # Allocation by status
    status_counts = (
        db.query(IPAllocation.status, func.count(IPAllocation.id))
        .group_by(IPAllocation.status)
        .all()
    )
    allocation_by_status = {s: c for s, c in status_counts}

    # Allocation by region
    region_counts = (
        db.query(Region.name, func.count(IPAllocation.id))
        .join(IPAllocation, Region.id == IPAllocation.region_id, isouter=True)
        .group_by(Region.id, Region.name)
        .all()
    )
    allocation_by_region = [{"region_name": name, "count": c} for name, c in region_counts]

    # Recent changes
    recent = (
        db.query(ChangeLog)
        .order_by(ChangeLog.created_at.desc())
        .limit(10)
        .all()
    )
    recent_changes = []
    for cl in recent:
        recent_changes.append({
            "id": cl.id,
            "entity_type": cl.entity_type,
            "action": cl.action,
            "operator": cl.operator,
            "summary": _build_summary(cl),
            "created_at": cl.created_at.isoformat(),
        })

    return {
        "total_regions": total_regions,
        "total_plane_types": total_plane_types,
        "total_allocations": total_allocations,
        "total_change_logs": total_change_logs,
        "allocation_by_status": allocation_by_status,
        "allocation_by_region": allocation_by_region,
        "recent_changes": recent_changes,
    }


def _build_summary(cl: ChangeLog) -> str:
    if cl.action == "create":
        return f"创建了 {cl.entity_type}: {cl.new_value or ''}"
    elif cl.action == "update":
        return f"更新了 {cl.entity_type} {cl.field_name or ''}: {cl.old_value or ''} -> {cl.new_value or ''}"
    elif cl.action == "delete":
        return f"删除了 {cl.entity_type}: {cl.old_value or ''}"
    elif cl.action == "import":
        return f"批量导入 IP 分配: {cl.new_value or ''}"
    return f"{cl.action} {cl.entity_type}"
