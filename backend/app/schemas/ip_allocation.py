from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AllocationBase(BaseModel):
    plane_type_id: str
    ip_range: str = Field(..., max_length=43)
    vlan_id: Optional[int] = None
    gateway: Optional[str] = Field(None, max_length=39)
    subnet_mask: Optional[str] = Field(None, max_length=15)
    purpose: Optional[str] = ""
    status: str = "active"


class AllocationCreate(AllocationBase):
    pass


class AllocationUpdate(BaseModel):
    ip_range: Optional[str] = Field(None, max_length=43)
    vlan_id: Optional[int] = None
    gateway: Optional[str] = Field(None, max_length=39)
    subnet_mask: Optional[str] = Field(None, max_length=15)
    purpose: Optional[str] = None
    status: Optional[str] = None


class AllocationResponse(AllocationBase):
    id: str
    region_id: str
    region_name: str = ""
    plane_type_name: str = ""
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
