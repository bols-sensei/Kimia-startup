"""Écriture dans audit_logs (valeurs sérialisables JSON)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import AuditLog


def _clean(value):
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_clean(v) for v in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def write_audit(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int,
    old_data: dict | None = None,
    new_data: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_data=_clean(old_data) if old_data is not None else None,
        new_data=_clean(new_data) if new_data is not None else None,
    )
    db.add(entry)
    return entry
