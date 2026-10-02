from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import check_password_strength

from app.models.auth import OwnershipStatus


# --------------------------------------------------------------------------- #
# Référentiels
# --------------------------------------------------------------------------- #

class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


# --------------------------------------------------------------------------- #
# Postes
# --------------------------------------------------------------------------- #

class PositionSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    skill: SkillRead


class PositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None
    is_active: bool
    display_order: int
    skills: list[SkillRead] = []
    users_count: int = 0


class PositionCreate(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = True
    display_order: int = 0
    skill_ids: list[int] = []


class PositionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    display_order: int | None = None
    skill_ids: list[int] | None = None


class SkillCreate(BaseModel):
    name: str


# --------------------------------------------------------------------------- #
# Utilisateurs
# --------------------------------------------------------------------------- #

class UserPositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    position: PositionRead
    is_primary: bool


class UserCreate(BaseModel):
    @field_validator("password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return check_password_strength(v)

    name: str
    email: EmailStr
    phone: str
    password: str
    role_id: int
    ownership_status: OwnershipStatus = OwnershipStatus.COLLABORATOR
    position_ids: list[int] = []
    primary_position_id: int | None = None
    skill_ids: list[int] = []

class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    role_id: int | None = None
    ownership_status: OwnershipStatus | None = None
    is_active: bool | None = None
    employment_status: Literal["ACTIVE", "ABSENT", "LEAVE", "SUSPENDED", "LEFT"] | None = None
    position_ids: list[int] | None = None
    primary_position_id: int | None = None

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    phone: str | None = None
    role: RoleRead
    positions: list[PositionRead] = []
    primary_position: PositionRead | None = None
    skills: list[SkillRead] = []
    ownership_status: OwnershipStatus
    is_active: bool
    employment_status: str = "ACTIVE"
    locked_until: datetime | None = None
    created_at: datetime
    permissions: list[str] = []
    has_password: bool = True


class UserSkillsUpdate(BaseModel):
    skill_ids: list[int]


# --------------------------------------------------------------------------- #
# Authentification
# --------------------------------------------------------------------------- #

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead

class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return check_password_strength(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return check_password_strength(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return check_password_strength(v)


class ResetLinkRead(BaseModel):
    token: str
    expires_at: datetime
    path: str
