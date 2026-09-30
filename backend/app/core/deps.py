"""
Dépendances FastAPI : session DB (réexportée), utilisateur courant depuis le JWT,
et garde-fous de permission — §18 : "le backend doit toujours vérifier les
permissions, le frontend n'est jamais une couche de sécurité".
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, selectinload

from app.core.security import decode_access_token
from app.database import get_db
from app.models import Role, RolePermission, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Récupère l'utilisateur courant depuis le JWT, avec ses permissions."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalide ou expirée",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_error

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error

    # Charger l'utilisateur + son rôle + ses permissions en une seule fois
    user = (
        db.query(User)
        .options(
            selectinload(User.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission),
        )
        .filter(User.id == int(user_id))
        .one_or_none()
    )
    if user is None:
        raise credentials_error

    # Même avec un JWT encore valide, revérifier que le compte est actif (§8)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé")

    return user


# --------------------------------------------------------------------------- #
# Ancien système : par nom de rôle (conservé pour compatibilité)
# --------------------------------------------------------------------------- #
def require_roles(*allowed_role_names: str):
    """
    Usage : Depends(require_roles("CEO", "DA"))

    ⚠️ Déprécié : préférer require_permission() qui est plus flexible.
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in allowed_role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé pour ce rôle",
            )
        return current_user

    return checker


# --------------------------------------------------------------------------- #
# Nouveau système : par permission (recommandé)
# --------------------------------------------------------------------------- #
def require_permission(*required_codes: str):
    """
    Usage : Depends(require_permission("finance.view"))

    L'utilisateur doit posséder TOUTES les permissions listées.
    Le CEO possède implicitement toutes les permissions (via `*`).
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        # Récupérer les codes de permissions du rôle
        codes = {rp.permission.code for rp in current_user.role.role_permissions}

        # Wildcard CEO : "*" donne tous les droits
        if "*" in codes:
            return current_user

        missing = [c for c in required_codes if c not in codes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission manquante : {', '.join(missing)}",
            )
        return current_user

    return checker


def require_any_permission(*required_codes: str):
    """
    Usage : Depends(require_any_permission("finance.view", "finance.edit"))

    L'utilisateur doit posséder AU MOINS UNE des permissions listées.
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        codes = {rp.permission.code for rp in current_user.role.role_permissions}

        if "*" in codes:
            return current_user

        if not any(c in codes for c in required_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission requise : une de {', '.join(required_codes)}",
            )
        return current_user

    return checker