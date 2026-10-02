"""
Espace Développement.
- membre dev (MEMBER)  : appartient à l'équipe dev, accès limité, par décision du CEO ;
- dev interne (INTERNAL): en plus, accès aux outils internes (require_dev_internal).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.deps import require_dev_internal, require_permission
from app.database import get_db
from app.models import DevMembership, User
from app.schemas.access import DevMemberRead, DevMemberSet

router = APIRouter()

# Catalogue statique des outils internes ; à rendre configurable plus tard.
INTERNAL_TOOLS = [
    {"key": "repositories", "label": "Dépôts de code"},
    {"key": "documentation", "label": "Documentation / API"},
    {"key": "environments", "label": "Environnements"},
]


def _read(m: DevMembership, u: User) -> DevMemberRead:
    return DevMemberRead(user_id=u.id, name=u.name, email=u.email, level=m.level, note=m.note, created_at=m.created_at)


@router.get("/members", response_model=list[DevMemberRead])
def list_members(db: Session = Depends(get_db), _: User = Depends(require_permission("dev.view"))):
    rows = (
        db.query(DevMembership, User).join(User, User.id == DevMembership.user_id)
        .filter(User.is_active.is_(True)).order_by(User.name).all()
    )
    return [_read(m, u) for m, u in rows]


@router.put("/members/{user_id}", response_model=DevMemberRead)
def set_member(
    user_id: int,
    payload: DevMemberSet,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("dev.manage")),
):
    target = db.get(User, user_id)
    if target is None or target.email.startswith("deleted_"):
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    m = db.get(DevMembership, user_id)
    old = {"level": m.level} if m else None
    if m is None:
        m = DevMembership(user_id=user_id, level=payload.level, note=payload.note, granted_by=actor.id)
        db.add(m)
    else:
        m.level, m.note, m.granted_by = payload.level, payload.note, actor.id
    db.flush()
    write_audit(db, user_id=actor.id, action="dev.membership_set", entity_type="user", entity_id=user_id,
                old_data=old, new_data={"level": payload.level})
    db.commit()
    db.refresh(m)
    return _read(m, target)


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(user_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("dev.manage"))):
    m = db.get(DevMembership, user_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Ce utilisateur n'est pas dans l'équipe dev")
    write_audit(db, user_id=actor.id, action="dev.membership_removed", entity_type="user", entity_id=user_id,
                old_data={"level": m.level})
    db.delete(m)
    db.commit()


@router.get("/tools")
def internal_tools(_: User = Depends(require_dev_internal)):
    """Réservé aux devs internes."""
    return INTERNAL_TOOLS
