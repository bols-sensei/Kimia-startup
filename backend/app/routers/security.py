"""Interface /security du CEO (§20) : événements de sécurité, comptes bloqués,
sessions actives, déconnexion forcée, statistiques."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.core.ws_manager import manager
from app.database import get_db
from app.models import SecurityEvent, User

router = APIRouter()


# --------------------------------------------------------------------------- #
# Schémas
# --------------------------------------------------------------------------- #
class SecurityEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    email: str | None
    ip_address: str | None
    event_type: str
    success: bool
    created_at: datetime


class LockedAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    locked_until: datetime | None
    failed_login_attempts: int
    is_active: bool


class ActiveSessionRead(BaseModel):
    user_id: int
    name: str
    email: str
    role: str
    connections: int  # nombre de WebSockets ouverts pour cet utilisateur


class SecurityStats(BaseModel):
    """Statistiques agrégées pour le tableau de bord Sécurité."""
    total_events: int
    total_success: int
    total_failures: int
    unique_ips: int
    locked_accounts: int
    daily: list[dict]  # [{date: "2026-09-29", success: 5, failures: 2}, ...]


# --------------------------------------------------------------------------- #
# Routes existantes
# --------------------------------------------------------------------------- #
@router.get("/events", response_model=dict)
def list_events(
    limit: int = 50,
    offset: int = 0,
    event_type: str | None = None,
    success: bool | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("CEO")),
):
    """Liste paginée des événements avec filtres."""
    query = db.query(SecurityEvent)

    if event_type:
        query = query.filter(SecurityEvent.event_type == event_type)
    if success is not None:
        query = query.filter(SecurityEvent.success.is_(success))
    if search:
        s = f"%{search}%"
        query = query.filter(
            (SecurityEvent.email.ilike(s)) | (SecurityEvent.ip_address.ilike(s))
        )
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
            query = query.filter(SecurityEvent.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
            # Inclure toute la journée
            dt = dt + timedelta(days=1)
            query = query.filter(SecurityEvent.created_at < dt)
        except ValueError:
            pass

    total = query.count()
    events = (
        query.order_by(SecurityEvent.created_at.desc())
        .offset(offset)
        .limit(min(limit, 500))
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [SecurityEventRead.model_validate(e).model_dump() for e in events],
    }


@router.get("/locked-accounts", response_model=list[LockedAccountRead])
def locked_accounts(db: Session = Depends(get_db), _: User = Depends(require_roles("CEO"))):
    now = datetime.now(timezone.utc)
    users = db.query(User).filter(User.locked_until.isnot(None)).all()
    return [
        u for u in users
        if (u.locked_until.replace(tzinfo=u.locked_until.tzinfo or timezone.utc)) > now
    ]


# --------------------------------------------------------------------------- #
# Sessions actives (via WebSocket)
# --------------------------------------------------------------------------- #
@router.get("/active-sessions", response_model=list[ActiveSessionRead])
def active_sessions(db: Session = Depends(get_db), _: User = Depends(require_roles("CEO"))):
    """Utilisateurs actuellement connectés via WebSocket."""
    result = []
    for user_id, conns in manager.active.items():
        if not conns:
            continue
        user = db.get(User, user_id)
        if user is None:
            continue
        result.append(
            ActiveSessionRead(
                user_id=user.id,
                name=user.name,
                email=user.email,
                role=user.role.name,
                connections=len(conns),
            )
        )
    result.sort(key=lambda s: s.name.lower())
    return result


@router.post("/active-sessions/{user_id}/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_user(user_id: int, _: User = Depends(require_roles("CEO"))):
    """Ferme toutes les WebSockets d'un utilisateur (déconnexion forcée)."""
    conns = manager.active.get(user_id, [])
    for ws in list(conns):
        try:
            await ws.close(code=4403)  # code personnalisé : "déconnecté par admin"
        except Exception:
            pass
    manager.active.pop(user_id, None)


# --------------------------------------------------------------------------- #
# Statistiques (pour le graphique)
# --------------------------------------------------------------------------- #
@router.get("/stats", response_model=SecurityStats)
def security_stats(db: Session = Depends(get_db), _: User = Depends(require_roles("CEO"))):
    """Statistiques globales + évolution journalière sur 7 jours."""
    total_events = db.query(SecurityEvent).count()
    total_success = db.query(SecurityEvent).filter(SecurityEvent.success.is_(True)).count()
    total_failures = total_events - total_success

    unique_ips = (
        db.query(func.count(func.distinct(SecurityEvent.ip_address)))
        .filter(SecurityEvent.ip_address.isnot(None))
        .scalar()
        or 0
    )

    now = datetime.now(timezone.utc)
    locked_count = len([u for u in db.query(User).filter(User.locked_until.isnot(None)).all()
                        if (u.locked_until.replace(tzinfo=u.locked_until.tzinfo or timezone.utc)) > now])

    # Évolution sur 7 jours
    seven_days_ago = now - timedelta(days=6)
    seven_days_ago = datetime(seven_days_ago.year, seven_days_ago.month, seven_days_ago.day, tzinfo=timezone.utc)

    events = (
        db.query(SecurityEvent)
        .filter(SecurityEvent.created_at >= seven_days_ago)
        .all()
    )

    daily_map: dict[str, dict] = defaultdict(lambda: {"success": 0, "failures": 0})
    for e in events:
        day = e.created_at.strftime("%Y-%m-%d")
        if e.success:
            daily_map[day]["success"] += 1
        else:
            daily_map[day]["failures"] += 1

    daily = []
    for i in range(7):
        day = (seven_days_ago + timedelta(days=i)).strftime("%Y-%m-%d")
        daily.append({
            "date": day,
            "success": daily_map[day]["success"],
            "failures": daily_map[day]["failures"],
        })

    return SecurityStats(
        total_events=total_events,
        total_success=total_success,
        total_failures=total_failures,
        unique_ips=unique_ips,
        locked_accounts=locked_count,
        daily=daily,
    )