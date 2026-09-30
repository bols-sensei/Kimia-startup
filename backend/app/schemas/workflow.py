from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.workflow import (
    ActivityPriority,
    ActivityStatus,
    AssignmentRole,
    ProjectCategory,
    ProjectServiceStatus,
    ProjectStatus,
    ProjectType,
    RequestStatus,
)

# --------------------------------------------------------------------------- #
# Demandes (public + interne)
# --------------------------------------------------------------------------- #


class PublicRequestCreate(BaseModel):
    """Utilisé par le site public (§14) : champs communs + form_data dynamique."""

    client_name: str
    client_phone: str
    client_email: EmailStr | None = None
    service_id: int
    event_type_id: int | None = None
    form_data: dict = Field(default_factory=dict)
    notes: str | None = None


class RequestStatusUpdate(BaseModel):
    new_status: RequestStatus
    reason: str | None = None


class RequestStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    old_status: RequestStatus | None
    new_status: RequestStatus
    changed_by: int | None
    reason: str | None
    created_at: datetime


class RequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference: str
    client_id: int
    service_id: int
    event_type_id: int | None
    status: RequestStatus
    form_data: dict
    notes: str | None
    agreed_amount: Decimal | None = None
    currency: str = "USD"
    event_date: date | None = None
    event_location: str | None = None
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Projets
# --------------------------------------------------------------------------- #


class ProjectServiceCreate(BaseModel):
    service_id: int
    agreed_amount: Decimal
    currency: str | None = None  # défaut = settings.default_currency si omis


class ProjectServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    service_id: int
    agreed_amount: Decimal
    currency: str
    status: ProjectServiceStatus


class ProjectCreate(BaseModel):
    client_id: int | None = None
    request_id: int | None = None
    name: str
    description: str | None = None
    project_type: ProjectType
    category: ProjectCategory
    responsible_id: int | None = None
    start_date: date | None = None
    planned_end_date: date | None = None
    event_date: date | None = None
    event_time: time | None = None
    event_location: str | None = None
    services: list[ProjectServiceCreate] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None
    responsible_id: int | None = None
    planned_end_date: date | None = None
    actual_end_date: date | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int | None
    request_id: int | None
    name: str
    description: str | None
    project_type: ProjectType
    category: ProjectCategory
    status: ProjectStatus
    responsible_id: int | None
    start_date: date | None
    planned_end_date: date | None
    actual_end_date: date | None
    event_date: date | None
    event_time: time | None
    event_location: str | None
    created_at: datetime
    updated_at: datetime


class ProjectDetailRead(ProjectRead):
    project_services: list[ProjectServiceRead] = []


# --------------------------------------------------------------------------- #
# Activités
# --------------------------------------------------------------------------- #


class ActivityCreate(BaseModel):
    """Création manuelle (hors génération automatique depuis un template — §21)."""

    project_id: int
    project_service_id: int | None = None
    name: str
    description: str | None = None
    required_skill_id: int | None = None
    priority: ActivityPriority = ActivityPriority.NORMALE
    start_at: datetime | None = None
    end_at: datetime | None = None


class ActivityUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ActivityStatus | None = None
    priority: ActivityPriority | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class ActivityAssignmentCreate(BaseModel):
    user_id: int
    assignment_role: AssignmentRole = AssignmentRole.PARTICIPANT


class ActivityAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    assignment_role: AssignmentRole


class ActivityChecklistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    label: str
    is_done: bool
    display_order: int


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    project_service_id: int | None
    template_id: int | None
    required_skill_id: int | None
    name: str
    description: str | None
    status: ActivityStatus
    priority: ActivityPriority
    start_at: datetime | None
    end_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ActivityDetailRead(ActivityRead):
    assignments: list[ActivityAssignmentRead] = []
    checklist_items: list[ActivityChecklistRead] = []


# --------------------------------------------------------------------------- #
# Documents / Notifications
# --------------------------------------------------------------------------- #


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    uploaded_by: int | None
    name: str
    path: str
    mime_type: str
    size: int
    created_at: datetime


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    title: str
    message: str
    project_id: int | None
    activity_id: int | None
    is_read: bool
    created_at: datetime

# --------------------------------------------------------------------------- #
# Création d'un projet depuis une demande
# --------------------------------------------------------------------------- #

class RequestProjectServiceCreate(BaseModel):
    """Prestation vendue dans un projet créé depuis une demande."""
    service_id: int
    agreed_amount: Decimal
    currency: str | None = None


class RequestCreateProject(BaseModel):
    """Payload pour transformer une demande en projet."""
    name: str
    description: str | None = None
    project_type: ProjectType = ProjectType.CLIENT
    category: ProjectCategory
    responsible_id: int | None = None
    start_date: date | None = None
    planned_end_date: date | None = None
    event_date: date | None = None
    event_time: time | None = None
    event_location: str | None = None
    services: list[RequestProjectServiceCreate] = []

class RequestUpdate(BaseModel):
    """Payload pour modifier une demande (CEO/DA)."""
    service_id: int | None = None
    event_type_id: int | None = None
    agreed_amount: Decimal | None = None
    currency: str | None = None
    event_date: date | None = None
    event_location: str | None = None
    notes: str | None = None