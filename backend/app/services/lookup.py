"""IP/CIDR 查询服务。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.exceptions import BusinessError
from app.models.ip_allocation import IPAllocation
from app.utils.ip_utils import parse_cidr, parse_ip


def lookup_allocations(db: Session, q: str, exact: bool = True) -> list[IPAllocation]:
    """按 IP 地址或 CIDR 查询 IP 分配记录。

    Args:
        db: 数据库会话。
        q: 查询字符串。可以是 IP 地址（如 10.0.0.5）或 CIDR（如 10.0.0.0/24）。
        exact: 是否精确匹配。True 只返回完全匹配的 CIDR，
               False 则返回所有与查询重叠的记录。

    Returns:
        匹配的 IPAllocation 对象列表。

    Raises:
        BusinessError: q 不是合法的 IP 或 CIDR 格式。
    """
    allocations = db.query(IPAllocation).all()
    results: list[IPAllocation] = []

    ip = parse_ip(q)
    net = parse_cidr(q) if not ip else None

    if ip:
        for a in allocations:
            existing = parse_cidr(a.ip_range)
            if existing and ip in existing:
                results.append(a)
    elif net:
        if exact:
            for a in allocations:
                existing = parse_cidr(a.ip_range)
                if existing and existing == net:
                    results.append(a)
        else:
            for a in allocations:
                existing = parse_cidr(a.ip_range)
                if existing and existing.overlaps(net):
                    results.append(a)
    else:
        raise BusinessError(f"Invalid IP address or CIDR: {q}")

    return results
