"""
Domaine Workflow : requests, request_status_history, projects, project_services,
activity_templates, checklist_template_items, activities, activity_assignments,
activity_checklists, documents, notifications.

Notifications est rattaché ici (pas de fichier dédié dans la structure imposée) car
il référence directement projects/activities/users du même domaine opérationnel.

Enums figés par le brief (§21, §23, §27) : RequestStatus, ProjectType, ProjectStatus,
ProjectCategory, ActivityStatus, ActivityPriority, AssignmentRole.
ProjectServiceStatus n'est PAS défini par le brief — valeurs posées ici par défaut
(PLANIFIE/EN_COURS/TERMINE/ANNULE), À CONFIRMER (point de décision ouvert).
"""

import enum
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database import Base


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class RequestStatus(str, enum.Enum):
    NOUVELLE = "NOUVELLE"
    A_CONTACTER = "A_CONTACTER"
    EN_DISCUSSION = "EN_DISCUSSION"
    CONFIRMEE = "CONFIRMEE"
    REFUSEE = "REFUSEE"
    ANNULEE = "ANNULEE"


class ProjectType(str, enum.Enum):
    CLIENT = "CLIENT"
    INTERNE = "INTERNE"


class ProjectCategory(str, enum.Enum):
    """Classification du projet — distincte de la catégorie du service vendu
    (Category/Service). Point de décision : redondance à clarifier avec
    project_services si un projet ne couvre qu'une seule catégorie en pratique."""

    PHOTOGRAPHIE = "PHOTOGRAPHIE"
    VIDEO = "VIDEO"
    GRAPHISME = "GRAPHISME"
    DEVELOPPEMENT_WEB = "DEVELOPPEMENT_WEB"
    COMMUNICATION = "COMMUNICATION"
    AUTRE = "AUTRE"


class ProjectStatus(str, enum.Enum):
    A_PREPARER = "A_PREPARER"
    EN_PREPARATION = "EN_PREPARATION"
    EN_COURS = "EN_COURS"
    LIVRAISON = "LIVRAISON"
    TERMINE = "TERMINE"
    ANNULE = "ANNULE"


class ProjectServiceStatus(str, enum.Enum):
    """Non définie par le brief — valeurs par défaut proposées, à valider."""

    PLANIFIE = "PLANIFIE"
    EN_COURS = "EN_COURS"
    TERMINE = "TERMINE"
    ANNULE = "ANNULE"


class ActivityStatus(str, enum.Enum):
    A_FAIRE = "A_FAIRE"
    EN_COURS = "EN_COURS"
    TERMINEE = "TERMINEE"
    BLOQUEE = "BLOQUEE"
    ANNULEE = "ANNULEE"


class ActivityPriority(str, enum.Enum):
    BASSE = "BASSE"
    NORMALE = "NORMALE"
    HAUTE = "HAUTE"
    URGENTE = "URGENTE"


class AssignmentRole(str, enum.Enum):
    RESPONSABLE = "RESPONSABLE"
    PARTICIPANT = "PARTICIPANT"


# --------------------------------------------------------------------------- #
# Commercial
# --------------------------------------------------------------------------- #


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"), nullable=False
    )
    event_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("event_types.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[RequestStatus] = mapped_column(default=RequestStatus.NOUVELLE, nullable=False)
    form_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Prix négocié (rempli par le CEO)
    agreed_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(
        String(3), default=lambda: settings.default_currency, nullable=False
    )

    # Champs éditables (extraits de form_data pour faciliter la modification)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    event_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    status_history: Mapped[list["RequestStatusHistory"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    project: Mapped["Project | None"] = relationship(back_populates="request")

class RequestStatusHistory(Base):
    __tablename__ = "request_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), nullable=False
    )
    old_status: Mapped[RequestStatus | None] = mapped_column(nullable=True)
    new_status: Mapped[RequestStatus] = mapped_column(nullable=False)
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped["Request"] = relationship(back_populates="status_history")


# --------------------------------------------------------------------------- #
# Projets
# --------------------------------------------------------------------------- #


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    # 0..1–0..1 avec Request : FK unique portée ici. Si un jour une demande doit
    # pouvoir générer plusieurs projets, retirer `unique=True` et inverser le sens.
    request_id: Mapped[int | None] = mapped_column(
        ForeignKey("requests.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_type: Mapped[ProjectType] = mapped_column(nullable=False)
    category: Mapped[ProjectCategory] = mapped_column(nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(default=ProjectStatus.A_PREPARER, nullable=False)
    responsible_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    event_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    event_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    request: Mapped["Request | None"] = relationship(back_populates="project")
    project_services: Mapped[list["ProjectService"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    activities: Mapped[list["Activity"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectService(Base):
    __tablename__ = "project_services"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"), nullable=False
    )
    agreed_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default=lambda: settings.default_currency, nullable=False)
    status: Mapped[ProjectServiceStatus] = mapped_column(
        default=ProjectServiceStatus.PLANIFIE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="project_services")
    activities: Mapped[list["Activity"]] = relationship(back_populates="project_service")


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #


class ActivityTemplate(Base):
    __tablename__ = "activity_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[ActivityPriority | None] = mapped_column(nullable=True)
    required_skill_id: Mapped[int | None] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    checklist_items: Mapped[list["ChecklistTemplateItem"]] = relationship(
        back_populates="activity_template", cascade="all, delete-orphan"
    )


class ChecklistTemplateItem(Base):
    __tablename__ = "checklist_template_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_template_id: Mapped[int] = mapped_column(
        ForeignKey("activity_templates.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    activity_template: Mapped["ActivityTemplate"] = relationship(back_populates="checklist_items")


# --------------------------------------------------------------------------- #
# Activités
# --------------------------------------------------------------------------- #


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    project_service_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_services.id", ondelete="SET NULL"), nullable=True
    )
    # Traçabilité uniquement : ne doit jamais bloquer la suppression d'un template.
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("activity_templates.id", ondelete="SET NULL"), nullable=True
    )
    required_skill_id: Mapped[int | None] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ActivityStatus] = mapped_column(default=ActivityStatus.A_FAIRE, nullable=False)
    priority: Mapped[ActivityPriority] = mapped_column(default=ActivityPriority.NORMALE, nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="activities")
    project_service: Mapped["ProjectService | None"] = relationship(back_populates="activities")
    assignments: Mapped[list["ActivityAssignment"]] = relationship(
        back_populates="activity", cascade="all, delete-orphan"
    )
    checklist_items: Mapped[list["ActivityChecklist"]] = relationship(
        back_populates="activity", cascade="all, delete-orphan"
    )


class ActivityAssignment(Base):
    __tablename__ = "activity_assignments"

    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    assignment_role: Mapped[AssignmentRole] = mapped_column(nullable=False)

    activity: Mapped["Activity"] = relationship(back_populates="assignments")


class ActivityChecklist(Base):
    __tablename__ = "activity_checklists"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    done_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    activity: Mapped["Activity"] = relationship(back_populates="checklist_items")


# --------------------------------------------------------------------------- #
# Documents
# --------------------------------------------------------------------------- #


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("size > 0", name="ck_document_size_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    # Limite haute appliquée aussi côté application (settings.max_document_size_bytes) :
    # la contrainte SQL fixe ne peut pas lire settings.* au moment du DDL, donc la
    # borne de 20 Mo est revérifiée en amont dans le router d'upload.
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="documents")


# --------------------------------------------------------------------------- #
# Notifications
# --------------------------------------------------------------------------- #


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # Type volontairement en texte libre (pas d'enum strict) : la liste des
    # événements WebSocket (request.created, activity.assigned, ...) continuera
    # de s'étoffer au fil du projet.
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id", ondelete="SET NULL"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
