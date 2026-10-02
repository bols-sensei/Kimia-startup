"""
Domaine Caisse — journal APPEND-ONLY.

Une transaction n'est jamais modifiée ni supprimée. Une erreur se corrige par
une écriture inverse (reversal_of_id + motif), ce qui conserve la traçabilité.
Après clôture de la journée, les lignes passent à CLOTUREE.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.database import Base

CASH_IN = "IN"
CASH_OUT = "OUT"
CASH_STATUS_RECORDED = "ENREGISTREE"
CASH_STATUS_CLOSED = "CLOTUREE"


class CashClosing(Base):
    __tablename__ = "cash_closings"

    id: Mapped[int] = mapped_column(primary_key=True)
    closing_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_in: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_out: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    counted_balance: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    difference: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CashTransaction(Base):
    __tablename__ = "cash_transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_cash_amount_positive"),
        CheckConstraint("direction in ('IN','OUT')", name="ck_cash_direction"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default=lambda: settings.default_currency, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    project_service_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_services.id", ondelete="SET NULL"), nullable=True
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=CASH_STATUS_RECORDED, nullable=False)
    closing_id: Mapped[int | None] = mapped_column(
        ForeignKey("cash_closings.id", ondelete="SET NULL"), nullable=True
    )
    reversal_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("cash_transactions.id", ondelete="RESTRICT"), unique=True, nullable=True
    )
    reversal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
