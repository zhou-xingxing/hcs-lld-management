from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

UserRole = Literal["administrator", "user"]


class RegionGrant(BaseModel):
    id: str
    name: str


class UserResponse(BaseModel):
    id: str
    username: str
    role: UserRole
    display_name: str
    is_active: bool
    regions: list[RegionGrant] = []
    created_at: str
    updated_at: str


class CurrentUserResponse(BaseModel):
    id: str
    username: str
    role: UserRole
    display_name: str
    is_active: bool
    regions: list[RegionGrant] = []
    permissions: list[str] = []


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: CurrentUserResponse


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=128)
    role: UserRole = "user"
    display_name: str = Field("", max_length=100)
    is_active: bool = True
    region_ids: list[str] = []


class UserUpdate(BaseModel):
    role: Optional[UserRole] = None
    display_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    region_ids: Optional[list[str]] = None


class PasswordReset(BaseModel):
    password: str = Field(..., min_length=1, max_length=128)
