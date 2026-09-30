from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr


# --------------------------------------------------------------------------- #
# Catégories
# --------------------------------------------------------------------------- #

class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    is_active: bool


# --------------------------------------------------------------------------- #
# Types d'événements
# --------------------------------------------------------------------------- #

class EventTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


# --------------------------------------------------------------------------- #
# Champs de formulaire
# --------------------------------------------------------------------------- #

class FormFieldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    label: str
    field_type: str
    options: dict | None = None


class ServiceFormFieldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    display_order: int
    is_required: bool
    form_field: FormFieldRead


# --------------------------------------------------------------------------- #
# Services (prestations)
# --------------------------------------------------------------------------- #

class ServiceCreate(BaseModel):
    category_id: int
    name: str
    description: str | None = None
    base_price: Decimal | None = None
    price_type: str = "FIXE"


class ServiceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    base_price: Decimal | None = None
    price_type: str | None = None
    is_active: bool | None = None


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category_id: int
    name: str
    description: str | None = None
    base_price: Decimal | None = None
    price_type: str = "FIXE"
    is_active: bool


class ServiceDetailRead(ServiceRead):
    """Vue enrichie utilisée par le site public pour construire le formulaire dynamique."""
    event_types: list[EventTypeRead] = []
    form_fields: list[ServiceFormFieldRead] = []


# --------------------------------------------------------------------------- #
# Clients
# --------------------------------------------------------------------------- #

class ClientCreate(BaseModel):
    name: str
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    notes: str | None = None


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime