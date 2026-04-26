from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ip_allocation import IPAllocation
from app.models.network_plane_type import NetworkPlaneType
from app.models.region_network_plane import RegionNetworkPlane
from app.services.change_log import log_change
from app.utils.ip_utils import find_overlapping, parse_cidr


def get_region_plane_tree(db: Session, region_id: str) -> list[dict]:
    """获取 Region 下所有网络平面的树形结构。

    返回嵌套的树形列表，根节点为 parent_id IS NULL 的平面，
    每个节点包含 children 列表。
    """
    all_planes = (
        db.query(RegionNetworkPlane)
        .filter(RegionNetworkPlane.region_id == region_id)
        .all()
    )

    # 构建内存字典，方便 O(1) 查找和拼装树
    plane_dict = {}
    for p in all_planes:
        alloc_count = (
            db.query(func.count(IPAllocation.id))
            .filter(IPAllocation.plane_id == p.id)
            .scalar()
            or 0
        )
        plane_dict[p.id] = {
            "id": p.id,
            "region_id": p.region_id,
            "plane_type_id": p.plane_type_id,
            "plane_type_name": p.plane_type.name if p.plane_type else "",
            "cidr": p.cidr,
            "parent_id": p.parent_id,
            "allocation_count": alloc_count,
            "children": [],
        }

    # 拼装树：将子节点挂到父节点的 children 列表中
    roots = []
    for pid, node in plane_dict.items():
        parent_pid = node["parent_id"]
        if parent_pid and parent_pid in plane_dict:
            plane_dict[parent_pid]["children"].append(node)
        else:
            roots.append(node)
    return roots


def enable_plane_for_region(
    db: Session, region_id: str, plane_type_id: str, cidr: str, operator: str
) -> RegionNetworkPlane:
    """为 Region 启用一个根网络平面（parent_id IS NULL），携带 CIDR。"""
    # 校验：同一 (region_id, plane_type_id) 不能有多个根平面
    existing_root = (
        db.query(RegionNetworkPlane)
        .filter(
            RegionNetworkPlane.region_id == region_id,
            RegionNetworkPlane.plane_type_id == plane_type_id,
            RegionNetworkPlane.parent_id.is_(None),
        )
        .first()
    )
    if existing_root:
        raise ValueError("该网络平面类型已存在根节点，不能重复创建")

    # 校验 CIDR 格式
    net = parse_cidr(cidr)
    if not net:
        raise ValueError(f"无效的 CIDR 格式: {cidr}")

    rp = RegionNetworkPlane(
        region_id=region_id,
        plane_type_id=plane_type_id,
        cidr=cidr,
    )
    db.add(rp)
    db.flush()

    pt = db.query(NetworkPlaneType).filter(NetworkPlaneType.id == plane_type_id).first()
    log_change(
        db,
        entity_type="region_network_plane",
        entity_id=rp.id,
        action="create",
        operator=operator,
        new_value=f"region={region_id}, plane_type={pt.name if pt else plane_type_id}, cidr={cidr}",
    )
    return rp


def create_child_plane(
    db: Session, region_id: str, parent_id: str, cidr: str, operator: str
) -> RegionNetworkPlane:
    """在指定父平面下创建子平面，深度最多 3 级。"""
    # 校验：父节点存在且属于同一 Region
    parent = db.query(RegionNetworkPlane).filter(
        RegionNetworkPlane.id == parent_id,
        RegionNetworkPlane.region_id == region_id,
    ).first()
    if not parent:
        raise ValueError("父平面不存在")
    if not parent.cidr:
        raise ValueError("父平面没有 CIDR 范围，无法添加子平面")

    # 校验：层级深度不超过 3 级（root=0, child=1, grandchild=2）
    depth = _get_plane_depth(db, parent)
    if depth >= 2:
        raise ValueError(f"已达到最大嵌套层级限制（3级），当前深度: {depth + 1}")

    # 校验：子 CIDR 必须在父 CIDR 范围内
    child_net = parse_cidr(cidr)
    parent_net = parse_cidr(parent.cidr)
    if not child_net or not parent_net:
        raise ValueError("无效的 CIDR 格式")
    # Python 3.7+ 用 subnet_of，3.7 以下用 supernet_of
    subnet_check = (
        child_net.subnet_of(parent_net)
        if hasattr(child_net, "subnet_of")
        else parent_net.supernet_of(child_net)
    )
    if not subnet_check:
        raise ValueError(f"子网 CIDR {cidr} 必须在父平面 CIDR {parent.cidr} 范围内")

    # 校验：兄弟平面之间 CIDR 不重叠
    siblings = (
        db.query(RegionNetworkPlane)
        .filter(RegionNetworkPlane.parent_id == parent_id)
        .all()
    )
    sibling_cidrs = [s.cidr for s in siblings if s.cidr]
    overlapped = find_overlapping(cidr, sibling_cidrs)
    if overlapped:
        raise ValueError(f"与兄弟平面 CIDR 重叠: {', '.join(overlapped)}")

    # 校验：不与父层已有的 IP 分配重叠
    parent_alloc_cidrs = [
        a.ip_range
        for a in db.query(IPAllocation).filter(IPAllocation.plane_id == parent_id).all()
    ]
    overlapped = find_overlapping(cidr, parent_alloc_cidrs)
    if overlapped:
        raise ValueError(f"与父平面的 IP 分配重叠: {', '.join(overlapped)}")

    child = RegionNetworkPlane(
        region_id=region_id,
        plane_type_id=parent.plane_type_id,
        cidr=cidr,
        parent_id=parent_id,
    )
    db.add(child)
    db.flush()

    pt = db.query(NetworkPlaneType).filter(NetworkPlaneType.id == parent.plane_type_id).first()
    log_change(
        db,
        entity_type="region_network_plane",
        entity_id=child.id,
        action="create",
        operator=operator,
        new_value=f"parent={parent_id}, plane_type={pt.name if pt else ''}, cidr={cidr}",
    )
    return child


def disable_plane_for_region(
    db: Session, region_id: str, plane_id: str, operator: str
) -> bool:
    """删除平面节点，级联删除所有子平面及其 IP 分配。

    级联由数据库 FK CASCADE 和 ORM cascade="all, delete-orphan" 共同保证。
    在删除前手动记录所有受影响实体的审计日志。
    """
    plane = db.query(RegionNetworkPlane).filter(
        RegionNetworkPlane.id == plane_id,
        RegionNetworkPlane.region_id == region_id,
    ).first()
    if not plane:
        return False

    # 递归收集所有子代平面 ID（用于审计日志）
    descendant_ids = _collect_descendant_ids(db, plane_id)
    all_plane_ids = [plane_id] + descendant_ids

    # 审计日志：记录被级联删除的 IP 分配
    for pid in all_plane_ids:
        allocs = db.query(IPAllocation).filter(IPAllocation.plane_id == pid).all()
        for a in allocs:
            log_change(
                db,
                entity_type="ip_allocation",
                entity_id=a.id,
                action="delete",
                operator=operator,
                old_value=f"由平面 {pid} 删除级联触发",
            )

    # 审计日志：记录被级联删除的子平面
    for child_id in descendant_ids:
        cp = db.get(RegionNetworkPlane, child_id)
        log_change(
            db,
            entity_type="region_network_plane",
            entity_id=child_id,
            action="delete",
            operator=operator,
            old_value=f"由父平面 {plane_id} 删除级联触发, cidr={cp.cidr if cp else ''}",
        )

    # 审计日志：记录本平面删除
    pt_name = plane.plane_type.name if plane.plane_type else "unknown"
    log_change(
        db,
        entity_type="region_network_plane",
        entity_id=plane_id,
        action="delete",
        operator=operator,
        old_value=f"region={region_id}, plane_type={pt_name}, cidr={plane.cidr}",
    )

    # ORM delete 会通过 cascade="all, delete-orphan" 级联删除 children 和 allocations
    db.delete(plane)
    db.flush()
    return True


def _get_plane_depth(db: Session, plane: RegionNetworkPlane) -> int:
    """递归计算平面节点的嵌套深度（root=0）。"""
    depth = 0
    current = plane
    while current.parent_id:
        depth += 1
        current = db.get(RegionNetworkPlane, current.parent_id)
        if not current:
            break
    return depth


def _collect_descendant_ids(db: Session, plane_id: str) -> list[str]:
    """递归收集所有后代平面 ID（深度优先）。"""
    result = []
    children = (
        db.query(RegionNetworkPlane)
        .filter(RegionNetworkPlane.parent_id == plane_id)
        .all()
    )
    for child in children:
        result.append(child.id)
        result.extend(_collect_descendant_ids(db, child.id))
    return result
