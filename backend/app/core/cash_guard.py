"""Limite du nombre de comptes pouvant écrire dans la caisse."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.core.access import can_write_cash
from app.models import Role, RolePermission, User


def count_cash_operators(db: Session) -> int:
    roles = (
        db.query(Role)
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
        .all()
    )
    ids = [r.id for r in roles if can_write_cash(r.permission_codes)]
    if not ids:
        return 0
    return (
        db.query(User)
        .filter(User.role_id.in_(ids), User.is_active.is_(True), ~User.email.like("deleted_%"))
        .count()
    )


def assert_cash_operator_limit(db: Session) -> None:
    """À appeler APRÈS un flush : annule tout si la limite est dépassée."""
    if count_cash_operators(db) > settings.max_cash_operators:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Limite atteinte : {settings.max_cash_operators} compte(s) actif(s) "
                "autorisé(s) à écrire dans la caisse."
            ),
        )
