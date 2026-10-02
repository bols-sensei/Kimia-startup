from sqlalchemy.orm import Session, selectinload
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user, require_any_permission, require_permission, user_can
from app.core.ws_manager import manager
from app.database import get_db
from app.models import (
    Activity,
    ActivityAssignment,
    ActivityChecklist,
    Notification,
    Skill,
    User,
    UserSkill,
)
from app.schemas.workflow import (
    ActivityAssignmentCreate,
    ActivityCreate,
    ActivityDetailRead,
    ActivityRead,
    ActivityUpdate,
)

router = APIRouter()


def _notify(db: Session, user_id: int, notif_type: str, title: str, message: str, activity_id: int) -> None:
    db.add(
        Notification(
            user_id=user_id, type=notif_type, title=title, message=message, activity_id=activity_id
        )
    )
    db.commit()
    manager.send_to_user_sync(user_id, {"type": "notification.created", "data": {"title": title}})


@router.get("", response_model=list[ActivityRead])
def list_activities(
    project_id: int | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_permission("activities.view", "activities.view_assigned")),
):
    query = db.query(Activity)
    if project_id is not None:
        query = query.filter(Activity.project_id == project_id)
    # CM : toujours limité à ses activités ; CEO/DA peuvent demander leur planning perso (mine=true).
    if not user_can(current_user, "activities.view") or mine:
        query = query.join(Activity.assignments).filter(
            ActivityAssignment.user_id == current_user.id
        )
    return query.order_by(Activity.start_at).all()


@router.get("/{activity_id}", response_model=ActivityDetailRead)
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("activities.view", "activities.view_assigned")),
):
    activity = (
        db.query(Activity)
        .options(selectinload(Activity.assignments), selectinload(Activity.checklist_items))
        .filter(Activity.id == activity_id)
        .one_or_none()
    )
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activité introuvable")
    return activity


@router.post("", response_model=ActivityRead, status_code=status.HTTP_201_CREATED)
def create_activity(
    payload: ActivityCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("activities.manage")),
):
    activity = Activity(**payload.model_dump())
    db.add(activity)
    db.commit()
    db.refresh(activity)
    manager.broadcast_sync({"type": "activity.created", "data": {"id": activity.id}})
    return activity


@router.patch("/{activity_id}", response_model=ActivityRead)
def update_activity(
    activity_id: int,
    payload: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_permission("activities.manage", "activities.complete")),
):
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activité introuvable")

    # CM : ne peut modifier que les activités qui lui sont assignées (§18).
    if not user_can(current_user, "activities.manage"):
        assigned_user_ids = {a.user_id for a in activity.assignments}
        if current_user.id not in assigned_user_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Activité non assignée")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(activity, field, value)
    db.add(activity)
    db.commit()
    db.refresh(activity)

    event_type = "activity.completed" if activity.status.value == "TERMINEE" else "activity.updated"
    manager.broadcast_sync({"type": event_type, "data": {"id": activity.id, "status": activity.status.value}})
    return activity


@router.get("/{activity_id}/suggested-users", response_model=list[int])
def suggest_users(
    activity_id: int, db: Session = Depends(get_db), _: User = Depends(require_any_permission("activities.manage", "activities.assign"))
):
    """Kimia suggère, CEO/DA valide — jamais d'auto-affectation (§24)."""
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activité introuvable")
    if activity.required_skill_id is None:
        return []
    rows = db.query(UserSkill.user_id).filter(UserSkill.skill_id == activity.required_skill_id).all()
    return [r[0] for r in rows]


@router.post("/{activity_id}/assignments", response_model=ActivityRead)
def assign_user(
    activity_id: int,
    payload: ActivityAssignmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("activities.assign")),
):
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activité introuvable")

    existing = (
        db.query(ActivityAssignment)
        .filter_by(activity_id=activity_id, user_id=payload.user_id)
        .one_or_none()
    )
    if existing is None:
        db.add(
            ActivityAssignment(
                activity_id=activity_id, user_id=payload.user_id, assignment_role=payload.assignment_role
            )
        )
        db.commit()

    _notify(
        db,
        payload.user_id,
        "activity.assigned",
        "Nouvelle activité assignée",
        f"L'activité « {activity.name} » vous a été assignée.",
        activity_id,
    )
    manager.broadcast_sync({"type": "activity.assigned", "data": {"id": activity_id, "user_id": payload.user_id}})
    db.refresh(activity)
    return activity


@router.patch("/{activity_id}/checklist/{item_id}", response_model=ActivityDetailRead)
def toggle_checklist_item(
    activity_id: int,
    item_id: int,
    is_done: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_permission("activities.manage", "activities.complete")),
):
    item = db.get(ActivityChecklist, item_id)
    if item is None or item.activity_id != activity_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élément introuvable")

    item.is_done = is_done
    item.done_by = current_user.id if is_done else None
    db.add(item)
    db.commit()

    activity = (
        db.query(Activity)
        .options(selectinload(Activity.assignments), selectinload(Activity.checklist_items))
        .filter(Activity.id == activity_id)
        .one()
    )
    manager.broadcast_sync({"type": "activity.updated", "data": {"id": activity_id}})
    return activity
