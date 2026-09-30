from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.deps import require_permission
from app.core.security import hash_password
from app.database import get_db
from app.models import (
    Position,
    PositionSkill,
    Role,
    RolePermission,
    Skill,
    User,
    UserPosition,
    UserSkill,
)
from app.schemas.auth import (
    PasswordReset,
    RoleRead,
    SkillRead,
    UserCreate,
    UserRead,
    UserSkillsUpdate,
    UserUpdate,
)

router = APIRouter()


# --------------------------------------------------------------------------- #
# Référentiels : rôles et compétences
# --------------------------------------------------------------------------- #

@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.view")),
):
    """Liste des rôles disponibles (CEO + DA)."""
    return db.query(Role).order_by(Role.name).all()


@router.get("/skills", response_model=list[SkillRead])
def list_skills(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.view")),
):
    """Liste des compétences disponibles (CEO + DA)."""
    return db.query(Skill).order_by(Skill.name).all()



# --------------------------------------------------------------------------- #
# Liste des membres
# --------------------------------------------------------------------------- #

@router.get("/team", response_model=list[UserRead])
def team(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.view")),
):
    """
    Vue équipe (§5 : DA a accès à l'équipe opérationnelle,
    pas à la gestion des utilisateurs).
    Exclut les comptes supprimés.
    """
    users = (
        db.query(User)
        .options(
            selectinload(User.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission),
            selectinload(User.user_positions)
            .selectinload(UserPosition.position),
            selectinload(User.user_skills).selectinload(UserSkill.skill),
        )
        .filter(~User.email.like("deleted_%"))   # exclure les supprimés
        .order_by(User.name)
        .all()
    )

    result = []
    for u in users:
        data = UserRead.model_validate(u)
        data.permissions = [rp.permission.code for rp in u.role.role_permissions]
        data.positions = [up.position for up in u.user_positions]
        data.primary_position = u.primary_position
        data.has_password = u.password_hash is not None
        result.append(data)
    return result


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.manage")),
):
    """Liste complète des utilisateurs (CEO uniquement)."""
    users = (
        db.query(User)
        .options(
            selectinload(User.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission),
            selectinload(User.user_positions)
            .selectinload(UserPosition.position),
            selectinload(User.user_skills).selectinload(UserSkill.skill),
        )
        .order_by(User.name)
        .all()
    )

    result = []
    for u in users:
        data = UserRead.model_validate(u)
        data.permissions = [rp.permission.code for rp in u.role.role_permissions]
        data.positions = [up.position for up in u.user_positions]
        data.primary_position = u.primary_position
        data.has_password = u.password_hash is not None
        result.append(data)
    return result

# --------------------------------------------------------------------------- #
# Création d'un membre
# --------------------------------------------------------------------------- #

@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.manage")),
):
    """Créer un membre (CEO uniquement)."""
    if db.query(User).filter(User.email == payload.email).one_or_none():
        raise HTTPException(status_code=409, detail="Email déjà utilisé")

    if db.get(Role, payload.role_id) is None:
        raise HTTPException(status_code=400, detail=f"Rôle {payload.role_id} inconnu")

    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role_id=payload.role_id,
        ownership_status=payload.ownership_status,
    )
    db.add(user)
    db.flush()

    # Associer les postes (multiples)
    for pos_id in payload.position_ids:
        if db.get(Position, pos_id) is None:
            raise HTTPException(status_code=400, detail=f"Poste {pos_id} inconnu")
        is_primary = (pos_id == payload.primary_position_id)
        db.add(UserPosition(user_id=user.id, position_id=pos_id, is_primary=is_primary))

    # Associer les compétences
    for skill_id in payload.skill_ids:
        if db.get(Skill, skill_id) is None:
            raise HTTPException(status_code=400, detail=f"Compétence {skill_id} inconnue")
        db.add(UserSkill(user_id=user.id, skill_id=skill_id))

    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------- #
# Modification d'un membre
# --------------------------------------------------------------------------- #

@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.manage")),
):
    """Modifier un membre (CEO uniquement)."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    # Champs simples
    simple_data = payload.model_dump(
        exclude_unset=True,
        exclude={"position_ids", "primary_position_id"},
    )
    for field, value in simple_data.items():
        setattr(user, field, value)

    # Postes (si fournis)
    if payload.position_ids is not None:
        db.query(UserPosition).filter(UserPosition.user_id == user.id).delete()
        for pos_id in payload.position_ids:
            if db.get(Position, pos_id) is None:
                raise HTTPException(status_code=400, detail=f"Poste {pos_id} inconnu")
            is_primary = (pos_id == payload.primary_position_id)
            db.add(UserPosition(user_id=user.id, position_id=pos_id, is_primary=is_primary))

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------- #
# Compétences d'un membre
# --------------------------------------------------------------------------- #

@router.put("/{user_id}/skills", response_model=UserRead)
def set_user_skills(
    user_id: int,
    payload: UserSkillsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.skills")),
):
    """Définir les compétences d'un membre (CEO + DA)."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    # Supprimer les anciennes compétences
    db.query(UserSkill).filter(UserSkill.user_id == user_id).delete()

    # Ajouter les nouvelles
    for skill_id in payload.skill_ids:
        if db.get(Skill, skill_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Compétence {skill_id} inconnue",
            )
        db.add(UserSkill(user_id=user_id, skill_id=skill_id))

    db.commit()
    db.refresh(user)
    return user

# --------------------------------------------------------------------------- #
# Réinitialiser le mot de passe d'un membre (CEO uniquement)
# --------------------------------------------------------------------------- #

@router.post("/{user_id}/reset-password", response_model=UserRead)
def reset_user_password(
    user_id: int,
    payload: PasswordReset,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.manage")),
):
    """Le CEO génère un nouveau mot de passe pour un membre."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    user.password_hash = hash_password(payload.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)
    db.commit()
    db.refresh(user)

    data = UserRead.model_validate(user)
    data.permissions = [rp.permission.code for rp in user.role.role_permissions]
    data.positions = [up.position for up in user.user_positions]
    data.primary_position = user.primary_position
    data.has_password = user.password_hash is not None
    return data


# --------------------------------------------------------------------------- #
# Bloquer / Débloquer un compte (CEO uniquement)
# --------------------------------------------------------------------------- #

@router.post("/{user_id}/toggle-active", response_model=UserRead)
def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("team.manage")),
):
    """Bloquer ou débloquer un compte."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas vous bloquer vous-même")

    user.is_active = not user.is_active
    db.add(user)
    db.commit()
    db.refresh(user)

    data = UserRead.model_validate(user)
    data.permissions = [rp.permission.code for rp in user.role.role_permissions]
    data.positions = [up.position for up in user.user_positions]
    data.primary_position = user.primary_position
    data.has_password = user.password_hash is not None
    return data


# --------------------------------------------------------------------------- #
# Supprimer un compte (soft delete, CEO uniquement)
# --------------------------------------------------------------------------- #

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("team.manage")),
):
    """
    Supprime un compte (soft delete).
    Le compte est désactivé et anonymisé, mais l'historique est conservé.
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte")

    # Soft delete : on désactive et on anonymise
    user.is_active = False
    user.email = f"deleted_{user.id}@kimia.local"
    user.name = f"[Supprimé] {user.name}"

    db.add(user)
    db.commit()