from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class LookupResult(BaseModel):
    id: str
    cidr: str
    region_name: str
    plane_type_name: str
    scope: str = "Global"
    vlan_id: Optional[int] = None
    gateway_position: Optional[str] = None
    gateway_ip: Optional[str] = None


class LookupResponse(BaseModel):
    results: list[LookupResult]
    total: int
