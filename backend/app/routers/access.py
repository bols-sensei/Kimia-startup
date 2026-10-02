"""
Rôles & permissions éditables (sans modifier le code) + « Mes accès ».

Garde-fous :
- le rôle CEO et le joker `*` ne sont pas modifiables via l'API ;
- un rôle ne peut pas recevoir `*` ;
- accorder une permission d'écriture de caisse respecte la limite de comptes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.access import PERMISSION_CATALOG, WILDCARD_EXCLUDED, effective_permissions, has_permission
from app.core.audit import write_audit
from app.core.cash_guard import assert_cash_operator_limit
from app.core.deps import get_current_user, require_permission
from app.database import get_db
from app.models import Permission, Role, RolePermission, User
from app.schemas.access import MyAccess, PermissionRead, RoleCreate, RoleDetail, RolePermissionsUpdate

router = APIRouter()

PROTECTED_ROLES = {"CEO"}

MODULE_ACTIONS = {
    "cash": ["view", "create", "cancel", "close", "audit", "export"],
    "finance": ["view", "manage"],
    "team": ["view", "manage", "skills"],
    "dev": ["view", "manage", "tools.use"],
}


def _detail(role: Role) -> RoleDetail:
    return RoleDetail(
        id=role.id,
        name=role.name,
        description=role.description,
        permission_codes=sorted(role.permission_codes),
        users_count=len(role.users),
    )


def _load_role(db: Session, role_id: int) -> Role:
    role = (
        db.query(Role)
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission), selectinload(Role.users))
        .filter(Role.id == role_id)
        .one_or_none()
    )
    if role is None:
        raise HTTPException(status_code=404, detail="Rôle introuvable")
    return role


def _validate_codes(db: Session, codes: list[str]) -> list[str]:
    codes = sorted(set(codes))
    if "*" in codes:
        raise HTTPException(status_code=400, detail="Le joker '*' ne peut pas être attribué à un rôle")
    known = {p.code for p in db.query(Permission).all()} | set(PERMISSION_CATALOG)
    unknown = [c for c in codes if c not in known]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Permission(s) inconnue(s) : {', '.join(unknown)}")
    return codes


def _apply_codes(db: Session, role: Role, codes: list[str]) -> None:
    db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
    db.flush()
    for code in codes:
        perm = db.query(Permission).filter_by(code=code).one_or_none()
        if perm is None:
            perm = Permission(code=code, description=PERMISSION_CATALOG.get(code, (None, None))[1])
            db.add(perm)
            db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.flush()
    db.expire(role)


@router.get("/permissions", response_model=list[PermissionRead])
def list_permissions(db: Session = Depends(get_db), _: User = Depends(require_permission("roles.manage"))):
    """Catalogue des permissions, groupé par module côté UI."""
    out = {code: PermissionRead(code=code, description=desc, module=module)
           for code, (module, desc) in PERMISSION_CATALOG.items()}
    for p in db.query(Permission).all():
        if p.code != "*" and p.code not in out:
            out[p.code] = PermissionRead(code=p.code, description=p.description, module=p.code.split(".")[0])
    return sorted(out.values(), key=lambda p: p.code)


@router.get("/roles", response_model=list[RoleDetail])
def list_roles_detail(db: Session = Depends(get_db), _: User = Depends(require_permission("roles.manage"))):
    roles = (
        db.query(Role)
        .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission), selectinload(Role.users))
        .order_by(Role.name)
        .all()
    )
    return [_detail(r) for r in roles]


@router.post("/roles", response_model=RoleDetail, status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("roles.manage"))):
    name = payload.name.strip().upper().replace(" ", "_")
    if db.query(Role).filter(Role.name == name).first():
        raise HTTPException(status_code=409, detail="Ce rôle existe déjà")
    codes = _validate_codes(db, payload.permission_codes)
    role = Role(name=name, description=payload.description)
    db.add(role)
    db.flush()
    _apply_codes(db, role, codes)
    write_audit(db, user_id=user.id, action="role.created", entity_type="role", entity_id=role.id,
                new_data={"name": name, "permissions": codes})
    db.commit()
    return _detail(_load_role(db, role.id))


@router.put("/roles/{role_id}/permissions", response_model=RoleDetail)
def set_role_permissions(
    role_id: int,
    payload: RolePermissionsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("roles.manage")),
):
    role = _load_role(db, role_id)
    if role.name in PROTECTED_ROLES or "*" in role.permission_codes:
        raise HTTPException(status_code=403, detail="Ce rôle est protégé et ne peut pas être modifié")
    codes = _validate_codes(db, payload.permission_codes)
    old = sorted(role.permission_codes)
    _apply_codes(db, role, codes)
    assert_cash_operator_limit(db)   # rollback + 409 si dépassement
    write_audit(db, user_id=user.id, action="role.permissions_updated", entity_type="role", entity_id=role.id,
                old_data={"permissions": old}, new_data={"permissions": codes})
    db.commit()
    return _detail(_load_role(db, role_id))


@router.get("/me", response_model=MyAccess)
def my_access(current_user: User = Depends(get_current_user)):
    """« Mes accès » : explique à l'utilisateur ce qu'il peut faire (lecture seule)."""
    codes = current_user.role.permission_codes
    modules = {
        module: {a: has_permission(codes, f"{module}.{a}") for a in actions}
        for module, actions in MODULE_ACTIONS.items()
    }
    membership = current_user.dev_membership
    return MyAccess(
        role=current_user.role.name,
        permissions=effective_permissions(codes),
        employment_status=current_user.employment_status,
        dev_level=membership.level if membership else None,
        modules=modules,
    )
