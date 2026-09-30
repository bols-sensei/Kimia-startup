from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.models import (
    Position,
    Role,
    RolePermission,
    SecurityEvent,
    User,
    UserPosition,
)
from app.schemas.auth import LoginRequest, TokenResponse, UserRead

router = APIRouter()


# --------------------------------------------------------------------------- #
# Helper : convertir un User en UserRead avec ses permissions et postes
# --------------------------------------------------------------------------- #
def _user_to_read(user: User) -> UserRead:
    """Convertit un User en UserRead, en injectant permissions et postes."""
    data = UserRead.model_validate(user)
    data.permissions = [rp.permission.code for rp in user.role.role_permissions]
    data.positions = [up.position for up in user.user_positions]
    data.primary_position = user.primary_position
    return data


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip_address = request.client.host if request.client else None

    # Charger l'utilisateur AVEC son rôle + permissions + postes + compétences
    user = (
        db.query(User)
        .options(
            selectinload(User.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission),
            selectinload(User.user_positions)
            .selectinload(UserPosition.position),
            selectinload(User.user_skills),
        )
        .filter(User.email == payload.email)
        .one_or_none()
    )

    def log_event(event_type: str, success: bool, user_id: int | None) -> None:
        db.add(
            SecurityEvent(
                user_id=user_id,
                email=payload.email,
                ip_address=ip_address,
                event_type=event_type,
                success=success,
            )
        )
        db.commit()

    if user is None:
        log_event("login", False, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
        )

    now = datetime.now(timezone.utc)
    locked_until = user.locked_until
    if locked_until is not None and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    if locked_until and locked_until > now:
        log_event("login_locked_account", False, user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Compte bloqué jusqu'à {locked_until.isoformat()}",
        )

    if not user.is_active:
        log_event("login_disabled_account", False, user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )

    if not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_login_attempts:
            user.locked_until = now + timedelta(minutes=settings.account_lock_minutes)
        db.add(user)
        log_event("login", False, user.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
        )

    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)
    log_event("login", True, user.id)

    token = create_access_token(user_id=user.id, role=user.role.name)
    return TokenResponse(access_token=token, user=_user_to_read(user))


# --------------------------------------------------------------------------- #
# Profil courant
# --------------------------------------------------------------------------- #
@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return _user_to_read(current_user)


# --------------------------------------------------------------------------- #
# Débloquer un compte (CEO uniquement)
# --------------------------------------------------------------------------- #
@router.post("/unlock/{user_id}", response_model=UserRead)
def unlock_account(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "CEO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Réservé au CEO",
        )

    user = (
        db.query(User)
        .options(
            selectinload(User.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission),
            selectinload(User.user_positions)
            .selectinload(UserPosition.position),
            selectinload(User.user_skills),
        )
        .filter(User.id == user_id)
        .one_or_none()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable",
        )

    user.locked_until = None
    user.failed_login_attempts = 0
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_to_read(user)