"""
Caisse — journal append-only.
Pas de PATCH ni de DELETE : on annule par écriture inverse motivée.
Le CEO (joker `*`) peut VOIR et AUDITER, mais pas écrire (voir core/access.py).
"""

import csv
import io
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.audit import write_audit
from app.core.deps import require_permission
from app.database import get_db
from app.core.ws_manager import manager
from app.models import AuditLog, Payment, Project, ProjectService, Revenue, Service, User
from app.models.cash import (
    CASH_IN,
    CASH_OUT,
    CASH_STATUS_CLOSED,
    CASH_STATUS_RECORDED,
    CashClosing,
    CashTransaction,
)
from app.schemas.cash import (
    CashAuditRead,
    CashBalance,
    CashReceivable,
    CashClosingCreate,
    CashClosingRead,
    CashReversal,
    CashTransactionCreate,
    CashTransactionRead,
)

router = APIRouter()

ZERO = Decimal("0")


# --------------------------------------------------------------------------- #
# Utilitaires
# --------------------------------------------------------------------------- #
def _today_closed(db: Session) -> bool:
    return db.query(CashClosing.id).filter(CashClosing.closing_date == date.today()).first() is not None


def _next_reference(db: Session) -> str:
    year = date.today().year
    count = db.query(func.count(CashTransaction.id)).filter(
        CashTransaction.reference.like(f"CAI-{year}-%")
    ).scalar()
    return f"CAI-{year}-{str(count + 1).zfill(5)}"


def _to_read(tx: CashTransaction, author: str | None) -> CashTransactionRead:
    data = CashTransactionRead.model_validate(tx)
    data.created_by_name = author
    return data


def _save_transaction(db: Session, tx: CashTransaction) -> None:
    """Insère avec retry si deux écritures simultanées obtiennent la même référence."""
    for _ in range(3):
        tx.reference = _next_reference(db)
        try:
            with db.begin_nested():
                db.add(tx)
                db.flush()
            return
        except IntegrityError:
            db.expire(tx) if tx in db else None
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Référence de caisse en conflit, réessayez")


def _totals(db: Session, *filters) -> tuple[Decimal, Decimal]:
    rows = (
        db.query(CashTransaction.direction, func.coalesce(func.sum(CashTransaction.amount), 0))
        .filter(*filters)
        .group_by(CashTransaction.direction)
        .all()
    )
    sums = {d: Decimal(str(v)) for d, v in rows}
    return sums.get(CASH_IN, ZERO), sums.get(CASH_OUT, ZERO)


# --------------------------------------------------------------------------- #
# Rapprochement caisse → finance
# --------------------------------------------------------------------------- #
def _paid_so_far(db: Session, project_service_id: int) -> Decimal:
    total = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .join(Revenue, Revenue.id == Payment.revenue_id)
        .filter(Revenue.project_service_id == project_service_id, Payment.voided_at.is_(None))
        .scalar()
    )
    return Decimal(str(total))


def _check_receivable(db: Session, ps: ProjectService, payload: CashTransactionCreate, currency: str) -> None:
    """Valide AVANT insertion qu'un encaissement peut devenir un paiement du projet."""
    if currency != ps.currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Devise différente de la prestation ({ps.currency}) : encaissement impossible",
        )
    remaining = ps.agreed_amount - _paid_so_far(db, ps.id)
    if payload.amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Montant supérieur au reste à payer de la prestation ({remaining} {ps.currency})",
        )


def _create_linked_payment(db: Session, tx: CashTransaction, ps: ProjectService, user: User) -> Payment:
    """Crée le paiement correspondant à un encaissement de caisse (même transaction DB)."""
    revenue = (
        db.query(Revenue).filter(Revenue.project_service_id == ps.id).order_by(Revenue.id).first()
    )
    if revenue is None:
        revenue = Revenue(project_service_id=ps.id, amount=ps.agreed_amount, currency=ps.currency)
        db.add(revenue)
        db.flush()
    payment = Payment(
        revenue_id=revenue.id,
        amount=tx.amount,
        paid_at=datetime.now(timezone.utc),
        method="CASH",
        notes=f"Encaissement caisse {tx.reference}",
        cash_transaction_id=tx.id,
    )
    db.add(payment)
    db.flush()
    write_audit(
        db, user_id=user.id, action="finance.payment.created_from_cash", entity_type="payment",
        entity_id=payment.id,
        new_data={"cash_reference": tx.reference, "project_service_id": ps.id, "amount": tx.amount},
    )
    return payment


def _void_linked_payment(db: Session, original: CashTransaction, user: User, reason: str) -> None:
    payment = (
        db.query(Payment)
        .filter(Payment.cash_transaction_id == original.id, Payment.voided_at.is_(None))
        .one_or_none()
    )
    if payment is None:
        return
    payment.voided_at = datetime.now(timezone.utc)
    write_audit(
        db, user_id=user.id, action="finance.payment.voided_from_cash", entity_type="payment",
        entity_id=payment.id,
        old_data={"amount": payment.amount, "cash_reference": original.reference},
        new_data={"reason": reason},
    )


# --------------------------------------------------------------------------- #
# Lecture (cash.view)
# --------------------------------------------------------------------------- #
@router.get("/balance", response_model=CashBalance)
def balance(db: Session = Depends(get_db), _: User = Depends(require_permission("cash.view"))):
    total_in, total_out = _totals(db)
    unclosed = db.query(func.count(CashTransaction.id)).filter(
        CashTransaction.status == CASH_STATUS_RECORDED
    ).scalar()
    last = db.query(func.max(CashClosing.closing_date)).scalar()
    return CashBalance(
        balance=total_in - total_out,
        total_in=total_in,
        total_out=total_out,
        unclosed_count=unclosed,
        last_closing_date=last,
        today_closed=_today_closed(db),
        currency=settings.default_currency,
    )


def _filtered_query(db, direction, tx_status, date_from, date_to):
    q = db.query(CashTransaction, User.name).join(User, User.id == CashTransaction.created_by)
    if direction:
        q = q.filter(CashTransaction.direction == direction)
    if tx_status:
        q = q.filter(CashTransaction.status == tx_status)
    if date_from:
        q = q.filter(CashTransaction.entry_date >= date_from)
    if date_to:
        q = q.filter(CashTransaction.entry_date <= date_to)
    return q


@router.get("/transactions", response_model=list[CashTransactionRead])
def list_transactions(
    direction: str | None = Query(default=None, pattern="^(IN|OUT)$"),
    tx_status: str | None = Query(default=None, alias="status", pattern="^(ENREGISTREE|CLOTUREE)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("cash.view")),
):
    rows = (
        _filtered_query(db, direction, tx_status, date_from, date_to)
        .order_by(CashTransaction.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_to_read(tx, name) for tx, name in rows]


def _csv_safe(value) -> str:
    """Neutralise l'injection de formules dans Excel/Sheets."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@router.get("/transactions/export.csv")
def export_transactions(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("cash.export")),
):
    rows = (
        _filtered_query(db, None, None, date_from, date_to)
        .order_by(CashTransaction.id)
        .all()
    )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["reference", "date", "sens", "montant", "devise", "categorie", "libelle", "statut", "annule_ref", "auteur"])
    for tx, author in rows:
        w.writerow([
            tx.reference, tx.entry_date.isoformat(), tx.direction, tx.amount, tx.currency,
            _csv_safe(tx.category), _csv_safe(tx.label), tx.status, tx.reversal_of_id or "", _csv_safe(author),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="caisse.csv"'},
    )


@router.get("/receivables", response_model=list[CashReceivable])
def receivables(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("cash.create")),
):
    """Prestations de projet avec un reste à payer : sert à rattacher un encaissement."""
    rows = (
        db.query(ProjectService, Project.name, Service.name)
        .join(Project, Project.id == ProjectService.project_id)
        .join(Service, Service.id == ProjectService.service_id)
        .order_by(ProjectService.id.desc())
        .limit(300)
        .all()
    )
    out = []
    for ps, project_name, service_name in rows:
        paid = _paid_so_far(db, ps.id)
        remaining = ps.agreed_amount - paid
        if remaining > 0:
            out.append(CashReceivable(
                project_service_id=ps.id, label=f"{project_name} — {service_name}", currency=ps.currency,
                agreed_amount=ps.agreed_amount, paid=paid, remaining=remaining,
            ))
    return out


@router.get("/closings", response_model=list[CashClosingRead])
def list_closings(
    limit: int = Query(default=60, ge=1, le=365),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("cash.view")),
):
    return db.query(CashClosing).order_by(CashClosing.closing_date.desc()).limit(limit).all()


@router.get("/audit", response_model=list[CashAuditRead])
def audit_trail(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("cash.audit")),
):
    return (
        db.query(AuditLog)
        .filter(AuditLog.entity_type.in_(["cash_transaction", "cash_closing"]))
        .order_by(AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


# --------------------------------------------------------------------------- #
# Écriture (permissions explicites, jamais couvertes par le joker "*")
# --------------------------------------------------------------------------- #
@router.post("/transactions", response_model=CashTransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: CashTransactionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("cash.create")),
):
    if _today_closed(db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La caisse est déjà clôturée pour aujourd'hui")
    currency = (payload.currency or settings.default_currency).upper()
    ps = None
    if payload.project_service_id is not None:
        ps = db.get(ProjectService, payload.project_service_id)
        if ps is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestation projet introuvable")
        if payload.direction == CASH_IN:
            _check_receivable(db, ps, payload, currency)

    tx = CashTransaction(
        direction=payload.direction,
        amount=payload.amount,
        currency=currency,
        category=payload.category,
        label=payload.label.strip(),
        project_service_id=payload.project_service_id,
        entry_date=date.today(),   # date imposée par le serveur : pas d'antidatage
        status=CASH_STATUS_RECORDED,
        created_by=user.id,
    )
    _save_transaction(db, tx)
    write_audit(
        db, user_id=user.id, action="cash.transaction.created", entity_type="cash_transaction",
        entity_id=tx.id,
        new_data={"reference": tx.reference, "direction": tx.direction, "amount": tx.amount,
                  "currency": tx.currency, "label": tx.label, "project_service_id": tx.project_service_id},
    )
    # Un encaissement rattaché à une prestation devient automatiquement un paiement.
    # (Une sortie rattachée n'est qu'une étiquette : aucune rémunération n'est créée.)
    if ps is not None and tx.direction == CASH_IN:
        _create_linked_payment(db, tx, ps, user)
    db.commit()
    db.refresh(tx)
    manager.broadcast_sync({"type": "cash.changed"})
    return _to_read(tx, user.name)


@router.post("/transactions/{tx_id}/reverse", response_model=CashTransactionRead, status_code=status.HTTP_201_CREATED)
def reverse_transaction(
    tx_id: int,
    payload: CashReversal,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("cash.cancel")),
):
    """Annule un mouvement par écriture inverse (l'original n'est jamais modifié)."""
    original = db.get(CashTransaction, tx_id)
    if original is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mouvement introuvable")
    if original.reversal_of_id is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une écriture d'annulation ne peut pas être annulée")
    if db.query(CashTransaction.id).filter(CashTransaction.reversal_of_id == original.id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce mouvement est déjà annulé")
    if _today_closed(db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La caisse est clôturée pour aujourd'hui : corrigez demain")

    reversal = CashTransaction(
        direction=CASH_OUT if original.direction == CASH_IN else CASH_IN,
        amount=original.amount,
        currency=original.currency,
        category=original.category,
        label=f"Annulation de {original.reference}",
        project_service_id=original.project_service_id,
        entry_date=date.today(),
        status=CASH_STATUS_RECORDED,
        reversal_of_id=original.id,
        reversal_reason=payload.reason.strip(),
        created_by=user.id,
    )
    _save_transaction(db, reversal)
    # L'annulation d'un encaissement annule aussi le paiement généré (sans le supprimer).
    _void_linked_payment(db, original, user, reversal.reversal_reason)
    write_audit(
        db, user_id=user.id, action="cash.transaction.reversed", entity_type="cash_transaction",
        entity_id=original.id,
        new_data={"reversal_reference": reversal.reference, "reason": reversal.reversal_reason},
    )
    db.commit()
    db.refresh(reversal)
    manager.broadcast_sync({"type": "cash.changed"})
    return _to_read(reversal, user.name)


@router.post("/closings", response_model=CashClosingRead, status_code=status.HTTP_201_CREATED)
def close_cash(
    payload: CashClosingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("cash.close")),
):
    """Clôture la journée : fige les mouvements ENREGISTREE en CLOTUREE."""
    if _today_closed(db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La caisse est déjà clôturée pour aujourd'hui")

    last = db.query(CashClosing).order_by(CashClosing.closing_date.desc()).first()
    opening = last.closing_balance if last else ZERO
    total_in, total_out = _totals(db, CashTransaction.status == CASH_STATUS_RECORDED)
    closing_balance = opening + total_in - total_out

    counted = payload.counted_balance
    closing = CashClosing(
        closing_date=date.today(),
        opening_balance=opening,
        total_in=total_in,
        total_out=total_out,
        closing_balance=closing_balance,
        counted_balance=counted,
        difference=(counted - closing_balance) if counted is not None else None,
        notes=payload.notes,
        closed_by=user.id,
    )
    db.add(closing)
    db.flush()

    db.query(CashTransaction).filter(CashTransaction.status == CASH_STATUS_RECORDED).update(
        {"status": CASH_STATUS_CLOSED, "closing_id": closing.id}, synchronize_session=False
    )
    write_audit(
        db, user_id=user.id, action="cash.closed", entity_type="cash_closing", entity_id=closing.id,
        new_data={"date": closing.closing_date, "closing_balance": closing_balance,
                  "counted_balance": counted, "difference": closing.difference},
    )
    db.commit()
    db.refresh(closing)
    manager.broadcast_sync({"type": "cash.changed"})
    return closing
