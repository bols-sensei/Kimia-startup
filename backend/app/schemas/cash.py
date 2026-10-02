from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CashTransactionCreate(BaseModel):
    direction: Literal["IN", "OUT"]
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    label: str = Field(min_length=2, max_length=255)
    category: str | None = Field(default=None, max_length=50)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    project_service_id: int | None = None


class CashReversal(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class CashTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference: str
    direction: str
    amount: Decimal
    currency: str
    category: str | None
    label: str
    project_service_id: int | None
    entry_date: date
    status: str
    closing_id: int | None
    reversal_of_id: int | None
    reversal_reason: str | None
    created_by: int
    created_by_name: str | None = None
    created_at: datetime


class CashBalance(BaseModel):
    balance: Decimal
    total_in: Decimal
    total_out: Decimal
    unclosed_count: int
    last_closing_date: date | None
    today_closed: bool
    currency: str


class CashClosingCreate(BaseModel):
    counted_balance: Decimal | None = Field(default=None, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=500)


class CashClosingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    closing_date: date
    opening_balance: Decimal
    total_in: Decimal
    total_out: Decimal
    closing_balance: Decimal
    counted_balance: Decimal | None
    difference: Decimal | None
    notes: str | None
    closed_by: int
    closed_at: datetime


class CashReceivable(BaseModel):
    project_service_id: int
    label: str
    currency: str
    agreed_amount: Decimal
    paid: Decimal
    remaining: Decimal


class CashAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    action: str
    entity_type: str
    entity_id: int
    old_data: dict | None
    new_data: dict | None
    created_at: datetime
