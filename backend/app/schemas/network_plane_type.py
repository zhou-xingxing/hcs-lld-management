from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PlaneTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = ""


class PlaneTypeCreate(PlaneTypeBase):
    pass


class PlaneTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class PlaneTypeResponse(PlaneTypeBase):
    id: str
    region_count: int = 0
    created_at: str

    model_config = {"from_attributes": True}
