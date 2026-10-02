"""
Helper pour créer des notifications et les diffuser via WebSocket.
"""

from sqlalchemy.orm import Session

from app.core.ws_manager import manager
from app.models import Notification, User


def notify(
    db: Session,
    *,
    user_id: int,
    notif_type: str,
    title: str,
    message: str,
    project_id: int | None = None,
    activity_id: int | None = None,
    broadcast: bool = True,
) -> Notification:
    """Crée une notification pour un utilisateur et la diffuse via WebSocket."""
    notif = Notification(
        user_id=user_id,
        type=notif_type,
        title=title,
        message=message,
        project_id=project_id,
        activity_id=activity_id,
    )
    db.add(notif)
    db.flush()

    if broadcast:
        manager.send_to_user_sync(
            user_id,
            {
                "type": "notification.created",
                "data": {
                    "id": notif.id,
                    "title": title,
                    "message": message,
                    "type": notif_type,
                },
            },
        )

    return notif


def notify_permission_holders(
    db: Session,
    permission: str,
    *,
    notif_type: str,
    title: str,
    message: str,
    project_id: int | None = None,
    activity_id: int | None = None,
    exclude_user_id: int | None = None,
) -> list[Notification]:
    """Notifie tous les comptes actifs dont le rôle accorde `permission` (joker inclus)."""
    from sqlalchemy.orm import selectinload

    from app.core.access import has_permission
    from app.models import Role, RolePermission

    users = (
        db.query(User)
        .options(selectinload(User.role).selectinload(Role.role_permissions).selectinload(RolePermission.permission))
        .filter(User.is_active.is_(True), ~User.email.like("deleted_%"))
        .all()
    )
    created = []
    for user in users:
        if exclude_user_id and user.id == exclude_user_id:
            continue
        if not has_permission(user.role.permission_codes, permission):
            continue
        created.append(notify(
            db, user_id=user.id, notif_type=notif_type, title=title, message=message,
            project_id=project_id, activity_id=activity_id,
        ))
    return created


def notify_staff(
    db: Session,
    *,
    notif_type: str,
    title: str,
    message: str,
    project_id: int | None = None,
    activity_id: int | None = None,
    exclude_user_id: int | None = None,
) -> list[Notification]:
    """Notifie l'équipe qui traite les demandes (permission requests.manage), et non plus des rôles nommés."""
    return notify_permission_holders(
        db, "requests.manage", notif_type=notif_type, title=title, message=message,
        project_id=project_id, activity_id=activity_id, exclude_user_id=exclude_user_id,
    )
