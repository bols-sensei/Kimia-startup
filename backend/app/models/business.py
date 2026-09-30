"""
Domaine "business" : Configuration (categories, services, event_types,
service_event_types, form_fields, service_form_fields) + Commercial (clients).

Assumption retenue (point de décision non tranché par le brief) :
`is_active` sur categories/services + ON DELETE RESTRICT partout où ces tables
sont référencées, pour ne jamais perdre l'historique (prix figé, templates
copiés). La suppression physique n'est donc pas censée arriver en usage normal ;
on désactive plutôt qu'on supprime.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    services: Mapped[list["Service"]] = relationship(back_populates="category")


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (UniqueConstraint("category_id", "name", name="uq_service_category_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # FIXE, SUR_DEVIS, A_PARTIR_DE
    price_type: Mapped[str] = mapped_column(String(20), default="FIXE", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["Category"] = relationship(back_populates="services")
    service_event_types: Mapped[list["ServiceEventType"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )
    service_form_fields: Mapped[list["ServiceFormField"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )
class EventType(Base):
    __tablename__ = "event_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Seules 3 valeurs validées pour l'instant : Conférence, Mariage, Anniversaire.
    # Table (pas enum) car de nouveaux types pourront être ajoutés sans migration.
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    service_event_types: Mapped[list["ServiceEventType"]] = relationship(
        back_populates="event_type", cascade="all, delete-orphan"
    )


class ServiceEventType(Base):
    __tablename__ = "service_event_types"

    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), primary_key=True
    )
    event_type_id: Mapped[int] = mapped_column(
        ForeignKey("event_types.id", ondelete="CASCADE"), primary_key=True
    )

    service: Mapped["Service"] = relationship(back_populates="service_event_types")
    event_type: Mapped["EventType"] = relationship(back_populates="service_event_types")


class FormField(Base):
    __tablename__ = "form_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    field_type: Mapped[str] = mapped_column(String(30), nullable=False)  # text/date/select/...
    options: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # pour les champs select

    service_form_fields: Mapped[list["ServiceFormField"]] = relationship(
        back_populates="form_field", cascade="all, delete-orphan"
    )


class ServiceFormField(Base):
    __tablename__ = "service_form_fields"

    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), primary_key=True
    )
    form_field_id: Mapped[int] = mapped_column(
        ForeignKey("form_fields.id", ondelete="CASCADE"), primary_key=True
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    service: Mapped["Service"] = relationship(back_populates="service_form_fields")
    form_field: Mapped["FormField"] = relationship(back_populates="service_form_fields")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

