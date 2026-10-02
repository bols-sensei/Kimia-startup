from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.core.audit import write_audit
from app.core.deps import get_current_user, user_can
from app.core.notifications import notify, notify_permission_holders
from app.core.ratelimit import enforce_ip_limit
from app.core.security import create_access_token, hash_password, hash_token, verify_password
from app.database import get_db
from app.models import (
    Position,
    Role,
    RolePermission,
    PasswordResetToken,
    SecurityEvent,
    User,
    UserPosition,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordConfirm,
    TokenResponse,
    UserRead,
)

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
    # Une même IP ne peut pas enchaîner les échecs (empêche aussi de verrouiller le CEO en boucle)
    enforce_ip_limit(
        db, ip_address, ("login", "login_locked_account", "login_disabled_account"), settings.ip_max_failures
    )

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

    token = create_access_token(user_id=user.id, role=user.role.name, token_version=user.token_version)
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
    if not user_can(current_user, "security.manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission manquante : security.manage",
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


# --------------------------------------------------------------------------- #
# Mot de passe oublié / réinitialisation / changement
# --------------------------------------------------------------------------- #
def _security_event(db: Session, ip: str | None, email: str | None, event_type: str, success: bool, user_id: int | None) -> None:
    db.add(SecurityEvent(user_id=user_id, email=email, ip_address=ip, event_type=event_type, success=success))


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Demande de réinitialisation. Réponse IDENTIQUE que le compte existe ou non (pas
    d'énumération). Les détenteurs de `team.manage` (CEO) sont notifiés et génèrent un lien.
    """
    ip = request.client.host if request.client else None
    enforce_ip_limit(db, ip, ("password_forgot",), settings.ip_forgot_max, only_failures=False)

    user = db.query(User).filter(User.email == payload.email).one_or_none()
    _security_event(db, ip, payload.email, "password_forgot", True, user.id if user else None)
    if user is not None and user.is_active:
        notify_permission_holders(
            db, "team.manage", notif_type="password.reset_requested",
            title="Demande de réinitialisation de mot de passe",
            message=f"{user.name} ({user.email}) a oublié son mot de passe. Générez-lui un lien depuis sa fiche membre.",
            exclude_user_id=user.id,
        )
    db.commit()
    return {"detail": "Si ce compte existe, le responsable a été prévenu."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordConfirm, request: Request, db: Session = Depends(get_db)):
    """Consomme un lien à usage unique : l'utilisateur choisit lui-même son mot de passe."""
    ip = request.client.host if request.client else None
    enforce_ip_limit(db, ip, ("password_reset",), settings.ip_forgot_max * 2)

    now = datetime.now(timezone.utc)
    row = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == hash_token(payload.token)).one_or_none()
    user = db.get(User, row.user_id) if row is not None else None
    if (
        row is None
        or row.used_at is not None
        or _aware(row.expires_at) < now
        or user is None
        or not user.is_active
    ):
        _security_event(db, ip, user.email if user else None, "password_reset", False, user.id if user else None)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lien invalide ou expiré")

    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1                  # révoque toutes les sessions existantes
    user.failed_login_attempts = 0
    user.locked_until = None
    row.used_at = now
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.id != row.id,        # le jeton consommé est conservé (historique)
    ).delete(synchronize_session=False)
    _security_event(db, ip, user.email, "password_reset", True, user.id)
    write_audit(db, user_id=user.id, action="user.password_reset_completed", entity_type="user", entity_id=user.id)
    # Alerte l'intéressé : si ce n'est pas lui, il le voit immédiatement
    notify(
        db, user_id=user.id, notif_type="security.password_changed",
        title="Mot de passe modifié",
        message="Le mot de passe de votre compte vient d'être modifié. Si ce n'est pas vous, prévenez le responsable.",
    )
    db.commit()
    return {"detail": "Mot de passe mis à jour. Reconnectez-vous."}


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Changement par l'utilisateur connecté (mot de passe actuel exigé). Retourne un nouveau jeton."""
    ip = request.client.host if request.client else None
    enforce_ip_limit(db, ip, ("password_change",), settings.ip_max_failures)

    if not verify_password(payload.current_password, current_user.password_hash):
        current_user.failed_login_attempts += 1
        if current_user.failed_login_attempts >= settings.max_login_attempts:
            current_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.account_lock_minutes)
        _security_event(db, ip, current_user.email, "password_change", False, current_user.id)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mot de passe actuel incorrect")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le nouveau mot de passe doit être différent")

    current_user.password_hash = hash_password(payload.new_password)
    current_user.token_version += 1
    current_user.failed_login_attempts = 0
    _security_event(db, ip, current_user.email, "password_change", True, current_user.id)
    write_audit(db, user_id=current_user.id, action="user.password_changed", entity_type="user", entity_id=current_user.id)
    db.commit()
    db.refresh(current_user)
    token = create_access_token(user_id=current_user.id, role=current_user.role.name, token_version=current_user.token_version)
    return TokenResponse(access_token=token, user=_user_to_read(current_user))
