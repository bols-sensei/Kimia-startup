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
    """Notifie tous les CEO et DA (sauf exclude_user_id s'il est fourni)."""
    from app.models import Role

    roles = db.query(Role).filter(Role.name.in_(["CEO", "DA"])).all()
    role_ids = [r.id for r in roles]

    staff = db.query(User).filter(
        User.role_id.in_(role_ids),
        User.is_active.is_(True),
    ).all()

    created = []
    for user in staff:
        if exclude_user_id and user.id == exclude_user_id:
            continue
        notif = notify(
            db,
            user_id=user.id,
            notif_type=notif_type,
            title=title,
            message=message,
            project_id=project_id,
            activity_id=activity_id,
        )
        created.append(notif)

    return created  