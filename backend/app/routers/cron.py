"""
Endpoint pour tâches planifiées.
À appeler via un cron externe (Render, Railway, GitHub Actions, etc.)
une fois par jour.
"""

from datetime import datetime, timedelta, timezone

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.notifications import notify
from app.database import get_db
from app.models import Activity, ActivityAssignment

router = APIRouter()


@router.post("/check-deadlines")
def check_deadlines(
    x_cron_secret: str = Header(None, alias="X-Cron-Secret"),
    db: Session = Depends(get_db),
):
    """
    Vérifie les activités dont l'échéance est demain (J-1)
    et notifie les personnes assignées.
    """
    expected = settings.cron_secret or settings.secret_key   # repli dev uniquement
    if not x_cron_secret or not hmac.compare_digest(x_cron_secret.encode(), expected.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non autorisé")

    now = datetime.now(timezone.utc)
    tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = tomorrow_start + timedelta(days=1)

    activities = (
        db.query(Activity)
        .filter(
            Activity.end_at >= tomorrow_start,
            Activity.end_at < tomorrow_end,
            Activity.status.in_(["A_FAIRE", "EN_COURS"]),
        )
        .all()
    )

    notified = 0
    for activity in activities:
        assignments = (
            db.query(ActivityAssignment)
            .filter(ActivityAssignment.activity_id == activity.id)
            .all()
        )
        for assignment in assignments:
            notify(
                db,
                user_id=assignment.user_id,
                notif_type="activity.due_soon",
                title="Échéance demain",
                message=f"L'activité « {activity.name} » est due demain.",
                project_id=activity.project_id,
                activity_id=activity.id,
            )
            notified += 1

    db.commit()
    return {"checked": len(activities), "notified": notified}