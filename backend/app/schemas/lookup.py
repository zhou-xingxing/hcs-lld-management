from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class LookupResult(BaseModel):
    id: str
    ip_range: str
    region_name: str
    plane_type_name: str
    vlan_id: Optional[int] = None
    gateway: Optional[str] = None
    subnet_mask: Optional[str] = None
    purpose: Optional[str] = None
    status: str


class LookupResponse(BaseModel):
    results: list[LookupResult]
    total: int
