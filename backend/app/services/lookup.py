"""IP/CIDR 查询服务。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.exceptions import BusinessError
from app.models.region_network_plane import RegionNetworkPlane
from app.utils.ip_utils import parse_cidr, parse_ip


def lookup_region_planes(db: Session, q: str, exact: bool = True) -> list[RegionNetworkPlane]:
    """按 IP 地址或 CIDR 查询 Region 网络平面。

    Args:
        db: 数据库会话。
        q: 查询字符串。可以是 IP 地址（如 10.0.0.5）或 CIDR（如 10.0.0.0/24）。
        exact: 是否精确匹配。True 只返回完全匹配的 CIDR，
               False 则返回所有与查询重叠的记录。

    Returns:
        匹配的 RegionNetworkPlane 对象列表。

    Raises:
        BusinessError: q 不是合法的 IP 或 CIDR 格式。
    """
    planes = db.query(RegionNetworkPlane).filter(RegionNetworkPlane.cidr.isnot(None)).all()
    results: list[RegionNetworkPlane] = []

    ip = parse_ip(q)
    net = parse_cidr(q) if not ip else None

    if ip:
        for plane in planes:
            existing = parse_cidr(plane.cidr or "")
            if existing and ip in existing:
                results.append(plane)
    elif net:
        if exact:
            for plane in planes:
                existing = parse_cidr(plane.cidr or "")
                if existing and existing == net:
                    results.append(plane)
        else:
            for plane in planes:
                existing = parse_cidr(plane.cidr or "")
                if existing and existing.overlaps(net):
                    results.append(plane)
    else:
        raise BusinessError(f"Invalid IP address or CIDR: {q}")

    return results
