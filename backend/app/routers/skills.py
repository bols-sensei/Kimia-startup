"""Compétences (skills) — CRUD réservé au CEO."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.database import get_db
from app.models import Skill, User
from app.schemas.auth import SkillCreate, SkillRead

router = APIRouter()


@router.get("", response_model=list[SkillRead])
def list_skills(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.view")),
):
    return db.query(Skill).order_by(Skill.name).all()


@router.post("", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
def create_skill(
    payload: SkillCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.manage")),
):
    if db.query(Skill).filter(Skill.name == payload.name).one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette compétence existe déjà")
    skill = Skill(name=payload.name)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.manage")),
):
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compétence introuvable")
    db.delete(skill)
    db.commit()