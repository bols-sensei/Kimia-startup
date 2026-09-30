from sqlalchemy.orm import Session, selectinload
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.notifications import notify_staff
from app.core.deps import require_roles
from app.core.ws_manager import manager
from app.database import get_db
from app.models import Platform, Publication, PublicationPlatform, User
from app.schemas.content import PlatformRead, PublicationCreate, PublicationRead, PublicationUpdate

router = APIRouter()

# Transitions §27 : le CM crée/modifie/soumet, CEO/DA valide ou demande une modification.
CM_ALLOWED_TARGETS = {"BROUILLON", "A_VALIDER"}
VALIDATOR_ALLOWED_TARGETS = {"VALIDE", "A_MODIFIER"}


def _sync_platforms(db: Session, publication: Publication, platform_ids: list[int]) -> None:
    db.query(PublicationPlatform).filter(
        PublicationPlatform.publication_id == publication.id
    ).delete()
    for platform_id in platform_ids:
        if db.get(Platform, platform_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Plateforme {platform_id} inconnue"
            )
        db.add(PublicationPlatform(publication_id=publication.id, platform_id=platform_id))


@router.get("/platforms", response_model=list[PlatformRead])
def list_platforms(db: Session = Depends(get_db), _: User = Depends(require_roles("CEO", "DA", "CM"))):
    return db.query(Platform).order_by(Platform.id).all()


@router.get("", response_model=list[PublicationRead])
def list_publications(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("CEO", "DA", "CM")),
):
    query = db.query(Publication)
    if project_id is not None:
        query = query.filter(Publication.project_id == project_id)
    return query.order_by(Publication.scheduled_at).all()


@router.post("", response_model=PublicationRead, status_code=status.HTTP_201_CREATED)
def create_publication(
    payload: PublicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("CEO", "DA", "CM")),
):
    data = payload.model_dump(exclude={"platform_ids"})
    publication = Publication(**data, created_by=current_user.id)
    db.add(publication)
    db.flush()
    _sync_platforms(db, publication, payload.platform_ids)
    db.commit()
    db.refresh(publication)
    manager.broadcast_sync({"type": "publication.created", "data": {"id": publication.id}})
    return publication


@router.patch("/{publication_id}", response_model=PublicationRead)
def update_publication(
    publication_id: int,
    payload: PublicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("CEO", "DA", "CM")),
):
    publication = db.get(Publication, publication_id)
    if publication is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication introuvable")

    if payload.status is not None:
        target = payload.status.value
        is_cm = current_user.role.name == "CM"
        if is_cm and target not in CM_ALLOWED_TARGETS:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Statut réservé à CEO/DA")
        if not is_cm and target not in VALIDATOR_ALLOWED_TARGETS and target not in CM_ALLOWED_TARGETS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statut invalide")

    data = payload.model_dump(exclude_unset=True, exclude={"platform_ids"})
    for field, value in data.items():
        setattr(publication, field, value)

    if payload.platform_ids is not None:
        _sync_platforms(db, publication, payload.platform_ids)

    db.add(publication)
    db.commit()
    db.refresh(publication)

    event_type = "publication.validated" if publication.status.value == "VALIDE" else "publication.updated"
    manager.broadcast_sync({"type": event_type, "data": {"id": publication.id}})
        # Notifier les CEO/DA quand une publication passe en A_VALIDER
    if publication.status.value == "A_VALIDER":
        notify_staff(
            db,
            notif_type="publication.to_validate",
            title="Publication à valider",
            message=f"« {publication.title} » attend votre validation.",
            project_id=publication.project_id,
            exclude_user_id=current_user.id,
        )
        db.commit()
    return publication
