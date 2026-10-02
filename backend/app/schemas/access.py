from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    description: str | None = None
    module: str | None = None


class RoleDetail(BaseModel):
    id: int
    name: str
    description: str | None = None
    permission_codes: list[str] = []
    users_count: int = 0


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50, pattern=r"^[A-Za-z0-9_ -]+$")
    description: str | None = None
    permission_codes: list[str] = []


class RolePermissionsUpdate(BaseModel):
    permission_codes: list[str]


class MyAccess(BaseModel):
    role: str
    permissions: list[str]
    employment_status: str
    dev_level: str | None = None
    modules: dict[str, dict[str, bool]]


class DevMemberRead(BaseModel):
    user_id: int
    name: str
    email: str
    level: str
    note: str | None = None
    created_at: datetime


class DevMemberSet(BaseModel):
    level: Literal["INTERNAL", "MEMBER"]
    note: str | None = Field(default=None, max_length=255)
