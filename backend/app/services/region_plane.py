from __future__ import annotations

import ipaddress
from typing import Any

from sqlalchemy.orm import Session

from app.exceptions import BusinessError
from app.models.network_plane_type import NetworkPlaneType
from app.models.region_network_plane import RegionNetworkPlane
from app.services.change_log import log_change
from app.utils.ip_utils import IPNetwork, find_overlapping, parse_cidr, parse_ip
from app.utils.time_utils import format_datetime


def get_region_plane_tree(db: Session, region_id: str) -> list[dict[str, Any]]:
    """获取 Region 下所有网络平面的树形结构。

    返回嵌套的树形列表，树结构来自全局 NetworkPlaneType.parent_id，
    RegionNetworkPlane 只提供当前 Region 的启用状态和 CIDR。

    Args:
        db: 数据库会话。
        region_id: Region ID。

    Returns:
        树形结构列表，每个节点包含 id、plane_type_id、cidr、
        parent_id、children 等字段。
    """
    all_planes = db.query(RegionNetworkPlane).filter(RegionNetworkPlane.region_id == region_id).all()

    # 构建内存字典，方便 O(1) 查找和拼装树
    plane_dict: dict[str, dict[str, Any]] = {}
    plane_by_type_id = {p.plane_type_id: p for p in all_planes}
    for p in all_planes:
        plane_dict[p.id] = {
            "id": p.id,
            "region_id": p.region_id,
            "plane_type_id": p.plane_type_id,
            "plane_type_name": p.plane_type.name if p.plane_type else "",
            "cidr": p.cidr,
            "vlan_id": p.vlan_id,
            "gateway_position": p.gateway_position,
            "gateway_ip": p.gateway_ip,
            "parent_id": None,
            "plane_type_parent_id": p.plane_type.parent_id if p.plane_type else None,
            "created_at": format_datetime(p.created_at),
            "updated_at": format_datetime(p.updated_at),
            "children": [],
        }

    # 拼装树：将子节点挂到同 Region 中已启用的父类型节点下
    roots = []
    for plane in all_planes:
        node = plane_dict[plane.id]
        type_parent_id = plane.plane_type.parent_id if plane.plane_type else None
        parent_plane = plane_by_type_id.get(type_parent_id) if type_parent_id else None
        if parent_plane and parent_plane.id in plane_dict:
            node["parent_id"] = parent_plane.id
            plane_dict[parent_plane.id]["children"].append(node)
        else:
            roots.append(node)
    return roots


def enable_plane_for_region(
    db: Session,
    region_id: str,
    plane_type_id: str,
    cidr: str,
    operator: str,
    *,
    vlan_id: int | None = None,
    gateway_position: str | None = None,
    gateway_ip: str | None = None,
) -> tuple[RegionNetworkPlane, str | None]:
    """为 Region 启用一个网络平面类型。

    Args:
        db: 数据库会话。
        region_id: Region ID。
        plane_type_id: 网络平面类型 ID。
        cidr: 根平面的 CIDR 范围。
        operator: 操作者名称。
        vlan_id: VLAN ID，可选。
        gateway_position: 网关位置，可选。
        gateway_ip: 网关 IP 地址，可选。

    Returns:
        新创建的 RegionNetworkPlane 对象和可选弱校验提示。

    Raises:
        BusinessError: 该类型已启用、CIDR 格式无效、父级未启用或 CIDR 越界。
    """
    pt = db.query(NetworkPlaneType).filter(NetworkPlaneType.id == plane_type_id).first()
    if not pt:
        raise BusinessError("网络平面类型不存在")

    existing = (
        db.query(RegionNetworkPlane)
        .filter(
            RegionNetworkPlane.region_id == region_id,
            RegionNetworkPlane.plane_type_id == plane_type_id,
        )
        .first()
    )
    if existing:
        raise BusinessError("该网络平面类型已在 Region 中启用，不能重复创建")

    # 校验 CIDR 格式
    net = parse_cidr(cidr)
    if not net:
        raise BusinessError(f"无效的 CIDR 格式: {cidr}")
    gateway_ip_warning = _validate_gateway_ip_policy(net, gateway_ip, is_private=pt.is_private)

    parent_plane: RegionNetworkPlane | None = None
    if pt.parent_id:
        parent_plane = (
            db.query(RegionNetworkPlane)
            .filter(
                RegionNetworkPlane.region_id == region_id,
                RegionNetworkPlane.plane_type_id == pt.parent_id,
            )
            .first()
        )
        if not parent_plane:
            raise BusinessError("父级网络平面尚未在该 Region 启用")
        if not parent_plane.cidr:
            raise BusinessError("父级网络平面没有 CIDR 范围，无法启用子平面")
        parent_net = parse_cidr(parent_plane.cidr)
        if not parent_net:
            raise BusinessError("父级网络平面 CIDR 格式无效")
        subnet_check = net.subnet_of(parent_net) if hasattr(net, "subnet_of") else parent_net.supernet_of(net)
        if not subnet_check:
            raise BusinessError(f"子平面 CIDR {cidr} 必须在父平面 CIDR {parent_plane.cidr} 范围内")

        sibling_cidrs = _get_enabled_child_plane_cidrs(db, region_id, pt.parent_id)
        overlapped = find_overlapping(cidr, sibling_cidrs)
        if overlapped:
            raise BusinessError(f"与兄弟平面 CIDR 重叠: {', '.join(overlapped)}")

    rp = RegionNetworkPlane(
        region_id=region_id,
        plane_type_id=plane_type_id,
        cidr=cidr,
        vlan_id=vlan_id,
        gateway_position=gateway_position or None,
        gateway_ip=gateway_ip or None,
    )
    db.add(rp)
    db.flush()

    log_change(
        db,
        entity_type="region_network_plane",
        entity_id=rp.id,
        action="create",
        operator=operator,
        new_value=(
            f"region={region_id}, plane_type={pt.name}, cidr={cidr}, "
            f"vlan_id={vlan_id or ''}, gateway_position={gateway_position or ''}, gateway_ip={gateway_ip or ''}"
        ),
    )
    return rp, gateway_ip_warning


def create_child_plane(db: Session, region_id: str, parent_id: str, cidr: str, operator: str) -> RegionNetworkPlane:
    """兼容旧接口：子平面关系现在由 NetworkPlaneType.parent_id 维护。"""
    raise BusinessError("子平面关系由网络平面类型维护，请启用对应的子级网络平面类型")


def disable_plane_for_region(db: Session, region_id: str, plane_id: str, operator: str) -> bool:
    """删除平面节点，级联删除所有已启用的子类型平面。

    删除前手动记录所有受影响实体的审计日志。

    Args:
        db: 数据库会话。
        region_id: Region ID。
        plane_id: 要删除的平面节点 ID。
        operator: 操作者名称。

    Returns:
        删除成功返回 True，不存在时返回 False。
    """
    plane = (
        db.query(RegionNetworkPlane)
        .filter(
            RegionNetworkPlane.id == plane_id,
            RegionNetworkPlane.region_id == region_id,
        )
        .first()
    )
    if not plane:
        return False

    # 递归收集所有子代平面 ID（用于审计日志）
    descendant_ids = _collect_descendant_ids(db, plane)

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

    for child_id in reversed(descendant_ids):
        child = db.get(RegionNetworkPlane, child_id)
        if child:
            db.delete(child)
    db.delete(plane)
    db.flush()
    return True


def _collect_descendant_ids(db: Session, plane: RegionNetworkPlane) -> list[str]:
    """递归收集所有后代平面 ID（深度优先）。"""
    result: list[str] = []
    children = (
        db.query(RegionNetworkPlane)
        .join(NetworkPlaneType, RegionNetworkPlane.plane_type_id == NetworkPlaneType.id)
        .filter(
            RegionNetworkPlane.region_id == plane.region_id,
            NetworkPlaneType.parent_id == plane.plane_type_id,
        )
        .all()
    )
    for child in children:
        result.append(child.id)
        result.extend(_collect_descendant_ids(db, child))
    return result


def _get_enabled_child_plane_cidrs(db: Session, region_id: str, parent_type_id: str) -> list[str]:
    rows = (
        db.query(RegionNetworkPlane.cidr)
        .join(NetworkPlaneType, RegionNetworkPlane.plane_type_id == NetworkPlaneType.id)
        .filter(
            RegionNetworkPlane.region_id == region_id,
            NetworkPlaneType.parent_id == parent_type_id,
        )
        .all()
    )
    return [row[0] for row in rows if row[0]]


def _validate_gateway_ip_policy(net: IPNetwork, gateway_ip: str | None, *, is_private: bool) -> str | None:
    """强校验网关 IP 在 CIDR 内，弱校验网关 IP 是否符合推荐位置。"""
    if not gateway_ip:
        return None
    ip = parse_ip(gateway_ip)
    if not ip:
        raise BusinessError(f"无效的网关 IP 地址: {gateway_ip}")
    try:
        if ip not in net:
            raise BusinessError(f"网关 IP {gateway_ip} 必须在平面 CIDR {net.with_prefixlen} 范围内")
    except TypeError as exc:
        raise BusinessError(f"网关 IP {gateway_ip} 必须与平面 CIDR {net.with_prefixlen} 使用相同 IP 版本") from exc

    expected = _expected_gateway_ip(net, is_private=is_private)
    if ip != expected:
        position = "第一个可用 IP" if is_private else "最后一个可用 IP"
        plane_scope = "私网" if is_private else "非私网"
        return f"当前网关 IP 不符合推荐规则：{plane_scope}平面建议使用 CIDR 内{position} {expected}"
    return None


def _expected_gateway_ip(net: IPNetwork, *, is_private: bool) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    if net.num_addresses == 1:
        return net.network_address
    if is_private:
        if isinstance(net, ipaddress.IPv4Network) and net.prefixlen < 31:
            return net.network_address + 1
        if isinstance(net, ipaddress.IPv6Network) and net.prefixlen < 127:
            return net.network_address + 1
        return net.network_address
    if isinstance(net, ipaddress.IPv4Network):
        if net.prefixlen < 31:
            return net.broadcast_address - 1
        return net.broadcast_address
    return net.network_address + net.num_addresses - 1
