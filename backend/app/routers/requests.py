from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_permission
from app.core.ws_manager import manager
from app.database import get_db
from app.models import Notification, Request, RequestStatusHistory, User
from app.schemas.workflow import RequestRead, RequestStatusHistoryRead, RequestStatusUpdate
from datetime import datetime, timezone

from app.core.ws_manager import manager
from app.database import get_db
from app.models import (
    Channel, ChannelType, Client, Notification, Request, 
    RequestStatusHistory, Service, User,
)
from app.schemas.workflow import (
    RequestCreateProject, RequestRead, RequestStatusHistoryRead, RequestStatusUpdate,RequestUpdate, 
)
from app.services.project_service import create_project as create_project_service

router = APIRouter()

# Transitions autorisées (§16). REFUSEE/ANNULEE sont des culs-de-sac assumés.
ALLOWED_TRANSITIONS = {
    "NOUVELLE": {"A_CONTACTER", "REFUSEE", "ANNULEE"},
    "A_CONTACTER": {"EN_DISCUSSION", "REFUSEE", "ANNULEE"},
    "EN_DISCUSSION": {"CONFIRMEE", "REFUSEE", "ANNULEE"},
    "CONFIRMEE": {"ANNULEE"},
    "REFUSEE": set(),
    "ANNULEE": set(),
}


@router.get("", response_model=list[RequestRead])
def list_requests(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("requests.view")),
):
    query = db.query(Request)
    if status_filter:
        query = query.filter(Request.status == status_filter)
    return query.order_by(Request.created_at.desc()).all()


@router.get("/{request_id}", response_model=RequestRead)
def get_request(
    request_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("requests.view"))
):
    demande = db.get(Request, request_id)
    if demande is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable")
    return demande


@router.get("/{request_id}/history", response_model=list[RequestStatusHistoryRead])
def get_request_history(
    request_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("requests.view"))
):
    return (
        db.query(RequestStatusHistory)
        .filter(RequestStatusHistory.request_id == request_id)
        .order_by(RequestStatusHistory.created_at)
        .all()
    )


@router.patch("/{request_id}/status", response_model=RequestRead)
def update_request_status(
    request_id: int,
    payload: RequestStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("requests.manage")),
):
    demande = db.get(Request, request_id)
    if demande is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable")

    old_status = demande.status.value
    new_status = payload.new_status.value
    if new_status not in ALLOWED_TRANSITIONS.get(old_status, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transition {old_status} → {new_status} non autorisée",
        )

    demande.status = payload.new_status
    db.add(demande)
    db.add(
        RequestStatusHistory(
            request_id=demande.id,
            old_status=old_status,
            new_status=new_status,
            changed_by=current_user.id,
            reason=payload.reason,
        )
    )
    db.commit()
    db.refresh(demande)

    manager.broadcast_sync({"type": "request.updated", "data": {"id": demande.id, "status": new_status}})
    return demande
# --------------------------------------------------------------------------- #
# Créer un projet depuis une demande
# --------------------------------------------------------------------------- #

@router.post("/{request_id}/create-project", response_model=RequestRead)
def create_project_from_request(
    request_id: int,
    payload: RequestCreateProject,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("requests.manage")),
):
    """
    Transforme une demande CONFIRMEE en projet.
    - Crée le projet
    - Crée les ProjectService (prestations vendues)
    - Génère les activités depuis les templates
    - Crée le canal de discussion du projet
    - Notifie le responsable
    """
    demande = db.get(Request, request_id)
    if demande is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande introuvable",
        )

    if demande.status.value != "CONFIRMEE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seule une demande CONFIRMEE peut être transformée en projet",
        )

    if demande.project is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette demande a déjà un projet associé",
        )

    # Créer le projet via le service
    from app.schemas.workflow import ProjectCreate, ProjectServiceCreate

    project_data = ProjectCreate(
        client_id=demande.client_id,
        request_id=demande.id,
        name=payload.name,
        description=payload.description,
        project_type=payload.project_type,
        category=payload.category,
        responsible_id=payload.responsible_id,
        start_date=payload.start_date,
        planned_end_date=payload.planned_end_date,
        event_date=payload.event_date,
        event_time=payload.event_time,
        event_location=payload.event_location,
        services=[
            ProjectServiceCreate(
                service_id=svc.service_id,
                agreed_amount=svc.agreed_amount,
                currency=svc.currency,
            )
            for svc in payload.services
        ],
    )

    project = create_project_service(db, project_data)

    # Créer automatiquement le canal de discussion du projet
    channel = Channel(
        name=f"Projet · {project.name}",
        type=ChannelType.PROJECT,
        project_id=project.id,
    )
    db.add(channel)

    # Notifier le responsable
    if project.responsible_id:
        db.add(Notification(
            user_id=project.responsible_id,
            type="project.created",
            title="Nouveau projet assigné",
            message=f"Le projet « {project.name} » vous a été assigné.",
            project_id=project.id,
        ))
        manager.send_to_user_sync(
            project.responsible_id,
            {"type": "notification.created", "data": {"title": "Nouveau projet assigné"}},
        )

    db.commit()
    db.refresh(demande)

    # Diffuser la création
    manager.broadcast_sync({
        "type": "project.created",
        "data": {"id": project.id, "from_request": request_id},
    })

    return demande

# --------------------------------------------------------------------------- #
# Modifier une demande (CEO/DA)
# --------------------------------------------------------------------------- #

@router.patch("/{request_id}/details", response_model=RequestRead)
def update_request_details(
    request_id: int,
    payload: RequestUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("requests.manage")),
):
    """
    Modifier les détails d'une demande (prix, date, lieu, notes).
    Fonctionne à tout moment, même après confirmation.
    """
    demande = db.get(Request, request_id)
    if demande is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(demande, field, value)

    db.add(demande)
    db.commit()
    db.refresh(demande)

    manager.broadcast_sync({"type": "request.updated", "data": {"id": demande.id}})
    return demande