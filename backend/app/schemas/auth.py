from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

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