"""
Domaine Finance (MVP) : revenues, payments, remunerations.
Volontairement minimal — pas de comptabilité complète, pas de fiscalité (§30).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database import Base


class Revenue(Base):
    __tablename__ = "revenues"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_service_id: Mapped[int] = mapped_column(
        ForeignKey("project_services.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default=lambda: settings.default_currency, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="revenue", cascade="all, delete-orphan"
    )


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payment_amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    revenue_id: Mapped[int] = mapped_column(
        ForeignKey("revenues.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Paiement généré par un encaissement de caisse (rapprochement automatique).
    cash_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("cash_transactions.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    # Paiement annulé (jamais supprimé) : exclu des soldes, conservé pour l'historique.
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    revenue: Mapped["Revenue"] = relationship(back_populates="payments")


class Remuneration(Base):
    __tablename__ = "remunerations"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_service_id: Mapped[int] = mapped_column(
        ForeignKey("project_services.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default=lambda: settings.default_currency, nullable=False)
    status: Mapped[str | None] = mapped_column(String(30), nullable=True)  # ex: PENDING / PAID
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
