"""
Postes (positions) — configurables en base.
CRUD réservé au CEO.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.deps import require_permission
from app.database import get_db
from app.models import Position, PositionSkill, Skill, User
from app.schemas.auth import PositionCreate, PositionRead, PositionUpdate

router = APIRouter()


def _to_read(position: Position, users_count: int = 0) -> PositionRead:
    return PositionRead(
        id=position.id,
        name=position.name,
        description=position.description,
        is_active=position.is_active,
        display_order=position.display_order,
        skills=[ps.skill for ps in position.position_skills],
        users_count=users_count,
    )


@router.get("", response_model=list[PositionRead])
def list_positions(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.view")),
):
    """Liste des postes (accessible à CEO + DA)."""
    positions = (
        db.query(Position)
        .options(selectinload(Position.position_skills).selectinload(PositionSkill.skill))
        .order_by(Position.display_order, Position.name)
        .all()
    )

    result = []
    for p in positions:
        users_count = db.query(User).filter(User.position_id == p.id).count()
        result.append(_to_read(p, users_count))
    return result


@router.get("/{position_id}", response_model=PositionRead)
def get_position(
    position_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.view")),
):
    position = (
        db.query(Position)
        .options(selectinload(Position.position_skills).selectinload(PositionSkill.skill))
        .filter(Position.id == position_id)
        .one_or_none()
    )
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poste introuvable")
    return _to_read(position)


@router.post("", response_model=PositionRead, status_code=status.HTTP_201_CREATED)
def create_position(
    payload: PositionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.manage")),
):
    """Créer un poste (CEO uniquement)."""
    if db.query(Position).filter(Position.name == payload.name).one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce poste existe déjà")

    position = Position(
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
        display_order=payload.display_order,
    )
    db.add(position)
    db.flush()

    for skill_id in payload.skill_ids:
        if db.get(Skill, skill_id) is None:
            raise HTTPException(status_code=400, detail=f"Compétence {skill_id} inconnue")
        db.add(PositionSkill(position_id=position.id, skill_id=skill_id))

    db.commit()
    db.refresh(position)
    return _to_read(position)


@router.patch("/{position_id}", response_model=PositionRead)
def update_position(
    position_id: int,
    payload: PositionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.manage")),
):
    position = db.get(Position, position_id)
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poste introuvable")

    data = payload.model_dump(exclude_unset=True, exclude={"skill_ids"})
    for field, value in data.items():
        setattr(position, field, value)

    if payload.skill_ids is not None:
        db.query(PositionSkill).filter(PositionSkill.position_id == position.id).delete()
        for skill_id in payload.skill_ids:
            if db.get(Skill, skill_id) is None:
                raise HTTPException(status_code=400, detail=f"Compétence {skill_id} inconnue")
            db.add(PositionSkill(position_id=position.id, skill_id=skill_id))

    db.add(position)
    db.commit()
    db.refresh(position)
    return _to_read(position)


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(
    position_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.manage")),
):
    """Désactiver un poste (on ne supprime pas physiquement)."""
    position = db.get(Position, position_id)
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poste introuvable")

    # Vérifier qu'aucun utilisateur n'utilise ce poste
    users_count = db.query(User).filter(User.position_id == position.id).count()
    if users_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{users_count} membre(s) utilisent ce poste. Désactivez-le au lieu de le supprimer.",
        )

    db.delete(position)
    db.commit()