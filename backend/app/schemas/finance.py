from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RevenueCreate(BaseModel):
    project_service_id: int
    amount: Decimal
    currency: str | None = None


class RevenueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_service_id: int
    amount: Decimal
    currency: str
    created_at: datetime


class PaymentCreate(BaseModel):
    revenue_id: int
    amount: Decimal
    paid_at: datetime
    method: str | None = None
    notes: str | None = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    revenue_id: int
    amount: Decimal
    paid_at: datetime
    method: str | None
    notes: str | None
    cash_transaction_id: int | None = None
    voided_at: datetime | None = None


class RemunerationCreate(BaseModel):
    project_service_id: int
    user_id: int
    amount: Decimal
    currency: str | None = None
    status: str | None = None


class RemunerationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_service_id: int
    user_id: int
    amount: Decimal
    currency: str
    status: str | None
    created_at: datetime


class RevenueBalance(BaseModel):
    """Vue consolidée pour une prestation vendue : montant dû, payé, restant."""

    project_service_id: int
    agreed_amount: Decimal
    total_paid: Decimal
    remaining: Decimal
    total_remunerated: Decimal


class RevenueWithPayments(RevenueRead):
    payments: list[PaymentRead] = []


class FinanceDetail(RevenueBalance):
    """Balance + lignes de détail, pour l'écran Finance du CEO."""

    revenues: list[RevenueWithPayments] = []
    remunerations: list[RemunerationRead] = []
