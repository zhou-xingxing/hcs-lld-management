from __future__ import annotations

import ipaddress
from typing import Optional, Union

IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


def parse_cidr(cidr_str: str) -> Optional[IPNetwork]:
    """Parse a CIDR string into an IP network object.

    Args:
        cidr_str: CIDR 字符串，如 "10.0.0.0/24"。

    Returns:
        解析后的 IPv4Network 或 IPv6Network 对象。
        格式非法时返回 None。
    """
    try:
        return ipaddress.IPv4Network(cidr_str, strict=False)
    except (ValueError, TypeError):
        pass
    try:
        return ipaddress.IPv6Network(cidr_str, strict=False)
    except (ValueError, TypeError):
        pass
    return None


def parse_ip(ip_str: str) -> Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    """Parse an IP address string.

    Args:
        ip_str: IP 地址字符串，如 "10.0.0.5"。

    Returns:
        解析后的 IPv4Address 或 IPv6Address 对象。
        格式非法时返回 None。
    """
    try:
        return ipaddress.IPv4Address(ip_str)
    except (ValueError, TypeError):
        pass
    try:
        return ipaddress.IPv6Address(ip_str)
    except (ValueError, TypeError):
        pass
    return None


def check_overlap(net1: IPNetwork, net2: IPNetwork) -> bool:
    """Check if two CIDR networks overlap.

    Args:
        net1: 第一个网络对象。
        net2: 第二个网络对象。

    Returns:
        两个网络有重叠则返回 True。
    """
    return net1.overlaps(net2)


def find_overlapping(cidr_str: str, existing_cidrs: list[str]) -> list[str]:
    """Find which existing CIDRs overlap with the given CIDR.

    Args:
        cidr_str: 待检查的 CIDR 字符串。
        existing_cidrs: 已有 CIDR 列表。

    Returns:
        与 cidr_str 重叠的已有 CIDR 字符串列表。
    """
    target = parse_cidr(cidr_str)
    if not target:
        return []
    overlapping = []
    for ec in existing_cidrs:
        existing = parse_cidr(ec)
        if existing and check_overlap(target, existing):
            overlapping.append(ec)
    return overlapping


def ip_in_network(ip_str: str, cidr_str: str) -> bool:
    """Check if an IP address belongs to a CIDR network.

    Args:
        ip_str: IP 地址字符串。
        cidr_str: CIDR 字符串。

    Returns:
        IP 在网络的 CIDR 范围内则返回 True。
    """
    ip = parse_ip(ip_str)
    net = parse_cidr(cidr_str)
    if ip and net:
        return ip in net
    return False


def find_containing_networks(ip_str: str, existing_cidrs: list[str]) -> list[str]:
    """Find which existing CIDRs contain the given IP.

    Args:
        ip_str: IP 地址字符串。
        existing_cidrs: 已有 CIDR 列表。

    Returns:
        包含该 IP 的已有 CIDR 字符串列表。
    """
    ip = parse_ip(ip_str)
    if not ip:
        return []
    containing = []
    for ec in existing_cidrs:
        net = parse_cidr(ec)
        if net and ip in net:
            containing.append(ec)
    return containing
