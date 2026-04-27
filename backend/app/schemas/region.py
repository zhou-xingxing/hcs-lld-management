from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RegionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = ""


class RegionCreate(RegionBase):
    pass


class RegionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class RegionResponse(RegionBase):
    id: str
    plane_count: int = 0
    allocation_count: int = 0
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class RegionDetailResponse(RegionResponse):
    planes: list["RegionPlaneResponse"] = []


class RegionPlaneResponse(BaseModel):
    id: str
    region_id: str
    plane_type_id: str
    plane_type_name: str
    cidr: str | None = None
    parent_id: str | None = None
    plane_type_parent_id: str | None = None
    allocation_count: int = 0
    created_at: str
    updated_at: str
    children: list["RegionPlaneResponse"] = []

    model_config = {"from_attributes": True}


class RegionPlaneCreate(BaseModel):
    plane_type_id: str
    cidr: str = Field(..., max_length=43, description="CIDR 地址段，如 10.0.0.0/22")


class ChildPlaneCreate(BaseModel):
    cidr: str = Field(..., max_length=43, description="子网 CIDR，必须在父平面 CIDR 范围内")
