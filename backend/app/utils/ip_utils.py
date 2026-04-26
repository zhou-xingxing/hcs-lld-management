from __future__ import annotations

import ipaddress
from typing import Optional, Union

IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


def parse_cidr(cidr_str: str) -> Optional[IPNetwork]:
    """Parse a CIDR string, return None if invalid."""
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
    """Parse an IP address string."""
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
    """Check if two CIDR networks overlap."""
    return net1.overlaps(net2)


def find_overlapping(
    cidr_str: str, existing_cidrs: list[str]
) -> list[str]:
    """Find which existing CIDRs overlap with the given CIDR."""
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
    """Check if an IP address belongs to a CIDR network."""
    ip = parse_ip(ip_str)
    net = parse_cidr(cidr_str)
    if ip and net:
        return ip in net
    return False


def find_containing_networks(
    ip_str: str, existing_cidrs: list[str]
) -> list[str]:
    """Find which existing CIDRs contain the given IP."""
    ip = parse_ip(ip_str)
    if not ip:
        return []
    containing = []
    for ec in existing_cidrs:
        net = parse_cidr(ec)
        if net and ip in net:
            containing.append(ec)
    return containing
