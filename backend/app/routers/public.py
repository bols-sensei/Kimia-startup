"""
Endpoints consommés par le site public (non-PWA). Aucune authentification :
un visiteur anonyme doit pouvoir consulter le catalogue et envoyer une demande.
Le backend crée/retrouve le client par email/téléphone plutôt que d'exiger un
compte utilisateur (§16 : "un client n'est pas un utilisateur interne").
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from app.models import Category, Client, EventType, PortfolioItem, Request, Service
from app.schemas.content import PortfolioItemRead
from app.core.notifications import notify_staff
from app.core.ws_manager import manager
from app.database import get_db
from app.models import Category, Client, EventType, Request, Service
from app.schemas.business import (
    CategoryRead,
    EventTypeRead,
    ServiceDetailRead,
    ServiceFormFieldRead,
)
from app.schemas.workflow import PublicRequestCreate, RequestRead

router = APIRouter()


@router.get("/categories", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).filter(Category.is_active.is_(True)).all()


@router.get("/event-types", response_model=list[EventTypeRead])
def list_event_types(db: Session = Depends(get_db)):
    return db.query(EventType).all()


@router.get("/services", response_model=list[ServiceDetailRead])
def list_services(category_id: int | None = None, db: Session = Depends(get_db)):
    query = (
        db.query(Service)
        .options(
            selectinload(Service.service_event_types),
            selectinload(Service.service_form_fields),
        )
        .filter(Service.is_active.is_(True))
    )
    if category_id is not None:
        query = query.filter(Service.category_id == category_id)

    services = query.all()
    result = []
    for service in services:
        detail = ServiceDetailRead.model_validate(service)
        detail.event_types = [
            EventTypeRead.model_validate(link.event_type) for link in service.service_event_types
        ]
        detail.form_fields = [
            ServiceFormFieldRead.model_validate(link)
            for link in sorted(service.service_form_fields, key=lambda l: l.display_order)
        ]
        result.append(detail)
    return result


@router.post("/requests", response_model=RequestRead, status_code=status.HTTP_201_CREATED)
def submit_request(payload: PublicRequestCreate, db: Session = Depends(get_db)):
    service = db.get(Service, payload.service_id)
    if service is None or not service.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prestation invalide")

    # Un client existant est retrouvé par email (si fourni) ou téléphone, sinon créé.
    client = None
    if payload.client_email:
        client = db.query(Client).filter(Client.email == payload.client_email).one_or_none()
    if client is None:
        client = db.query(Client).filter(Client.phone == payload.client_phone).one_or_none()
    if client is None:
        client = Client(name=payload.client_name, phone=payload.client_phone, email=payload.client_email)
        db.add(client)
        db.flush()

       # Générer la référence unique
    year = datetime.now().year
    count = db.query(Request).filter(
        Request.reference.like(f"DEM-{year}-%")
    ).count()
    reference = f"DEM-{year}-{str(count + 1).zfill(4)}"

    # Extraire event_date et event_location depuis form_data
    event_date_str = payload.form_data.get("Date souhaitée") or payload.form_data.get("Date du mariage") or payload.form_data.get("Date de l'événement")
    event_location = payload.form_data.get("Lieu") or payload.form_data.get("Lieu de la cérémonie") or payload.form_data.get("Lieu de tournage")

    event_date = None
    if event_date_str:
        try:
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass

    demande = Request(
        reference=reference,
        client_id=client.id,
        service_id=payload.service_id,
        event_type_id=payload.event_type_id,
        form_data=payload.form_data,
        notes=payload.notes,
        event_date=event_date,
        event_location=event_location,
    )
    db.add(demande)
    db.commit()
    db.refresh(demande)

@router.get("/portfolio", response_model=list[PortfolioItemRead])
def list_portfolio(db: Session = Depends(get_db)):
    """Réalisations publiées, visibles sur le site public."""
    return (
        db.query(PortfolioItem)
        .filter(PortfolioItem.is_published.is_(True))
        .order_by(PortfolioItem.display_order, PortfolioItem.created_at.desc())
        .all()
    )