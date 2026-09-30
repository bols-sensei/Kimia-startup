"""
Services (catalogue) — CRUD réservé au CEO/DA.
Permet de modifier les prix, descriptions et statuts des prestations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.core.ws_manager import manager
from app.database import get_db
from app.models import Service, User
from app.schemas.business import ServiceRead, ServiceUpdate

router = APIRouter()


@router.get("", response_model=list[ServiceRead])
def list_services(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("CEO", "DA")),
):
    """Liste tous les services (actifs et inactifs) pour l'usage interne."""
    return db.query(Service).order_by(Service.category_id, Service.name).all()


@router.get("/{service_id}", response_model=ServiceRead)
def get_service(
    service_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("CEO", "DA")),
):
    service = db.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")
    return service


@router.patch("/{service_id}", response_model=ServiceRead)
def update_service(
    service_id: int,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("CEO", "DA")),
):
    """Modifier un service (prix, description, nom, statut actif)."""
    service = db.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service introuvable")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)

    db.add(service)
    db.commit()
    db.refresh(service)

    manager.broadcast_sync({"type": "service.updated", "data": {"id": service.id}})
    return service