"""Limitation par adresse IP, calculée sur security_events (valable multi-process, sans Redis).

⚠️ Derrière un reverse proxy, lancer uvicorn avec --proxy-headers --forwarded-allow-ips=<ip du proxy>,
sinon toutes les requêtes semblent venir du proxy et partagent le même compteur.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models import SecurityEvent


def enforce_ip_limit(
    db: Session,
    ip: str | None,
    event_types: tuple[str, ...],
    max_count: int,
    *,
    only_failures: bool = True,
) -> None:
    if not ip:
        return
    since = datetime.now(timezone.utc) - timedelta(minutes=settings.ip_window_minutes)
    query = db.query(func.count(SecurityEvent.id)).filter(
        SecurityEvent.ip_address == ip,
        SecurityEvent.created_at >= since,
        SecurityEvent.event_type.in_(event_types),
    )
    if only_failures:
        query = query.filter(SecurityEvent.success.is_(False))
    if query.scalar() >= max_count:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives depuis cette adresse. Réessayez plus tard.",
            headers={"Retry-After": str(settings.ip_window_minutes * 60)},
        )
