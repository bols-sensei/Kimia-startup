from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.content import PublicationFormat, PublicationStatus


class PlatformRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class PublicationCreate(BaseModel):
    project_id: int | None = None
    title: str
    content: str | None = None
    format: PublicationFormat | None = None
    scheduled_at: datetime | None = None
    media: dict | None = None
    notes: str | None = None
    platform_ids: list[int] = Field(default_factory=list)


class PublicationUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    format: PublicationFormat | None = None
    scheduled_at: datetime | None = None
    status: PublicationStatus | None = None
    media: dict | None = None
    notes: str | None = None
    platform_ids: list[int] | None = None


class PublicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int | None
    title: str
    content: str | None
    format: PublicationFormat | None
    scheduled_at: datetime | None
    status: PublicationStatus
    media: dict | None
    notes: str | None
    created_by: int | None
    platform_ids: list[int] = []
    created_at: datetime
    updated_at: datetime
class PortfolioItemCreate(BaseModel):
    title: str
    category: str
    description: str | None = None
    client_name: str | None = None
    image_path: str | None = None
    external_link: str | None = None
    project_id: int | None = None
    is_published: bool = False
    display_order: int = 0


class PortfolioItemUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    description: str | None = None
    client_name: str | None = None
    image_path: str | None = None
    external_link: str | None = None
    project_id: int | None = None
    is_published: bool | None = None
    display_order: int | None = None


class PortfolioItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    category: str
    description: str | None
    client_name: str | None
    image_path: str | None
    external_link: str | None
    project_id: int | None
    is_published: bool
    display_order: int
    created_at: datetime
    updated_at: datetime