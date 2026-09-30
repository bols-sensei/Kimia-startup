from decimal import Decimal

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import require_roles
from app.database import get_db
from app.models import Payment, ProjectService, Remuneration, Revenue, User
from app.schemas.finance import (
    PaymentCreate,
    PaymentRead,
    RemunerationCreate,
    RemunerationRead,
    FinanceDetail,
    RevenueBalance,
    RevenueCreate,
    RevenueRead,
)

router = APIRouter()


@router.post("/revenues", response_model=RevenueRead, status_code=status.HTTP_201_CREATED)
def create_revenue(
    payload: RevenueCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("CEO"))
):
    if db.get(ProjectService, payload.project_service_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestation projet introuvable")
    revenue = Revenue(**payload.model_dump())
    db.add(revenue)
    db.commit()
    db.refresh(revenue)
    return revenue


@router.post("/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("CEO"))
):
    if db.get(Revenue, payload.revenue_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revenu introuvable")
    payment = Payment(**payload.model_dump())
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/remunerations", response_model=RemunerationRead, status_code=status.HTTP_201_CREATED)
def create_remuneration(
    payload: RemunerationCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("CEO"))
):
    if db.get(ProjectService, payload.project_service_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestation projet introuvable")
    remuneration = Remuneration(**payload.model_dump())
    db.add(remuneration)
    db.commit()
    db.refresh(remuneration)
    return remuneration


@router.get("/project-services/{project_service_id}/detail", response_model=FinanceDetail)
def get_detail(
    project_service_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("CEO"))
):
    balance = get_balance(project_service_id, db, _)
    revenues = db.query(Revenue).filter(Revenue.project_service_id == project_service_id).all()
    remunerations = (
        db.query(Remuneration).filter(Remuneration.project_service_id == project_service_id).all()
    )
    return FinanceDetail(
        **balance.model_dump(), revenues=revenues, remunerations=remunerations
    )


@router.get("/project-services/{project_service_id}/balance", response_model=RevenueBalance)
def get_balance(
    project_service_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("CEO"))
):
    project_service = db.get(ProjectService, project_service_id)
    if project_service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestation projet introuvable")

    revenues = db.query(Revenue).filter(Revenue.project_service_id == project_service_id).all()
    total_paid = Decimal("0")
    for revenue in revenues:
        for payment in db.query(Payment).filter(Payment.revenue_id == revenue.id):
            total_paid += payment.amount

    remunerations = (
        db.query(Remuneration).filter(Remuneration.project_service_id == project_service_id).all()
    )
    total_remunerated = sum((r.amount for r in remunerations), Decimal("0"))

    return RevenueBalance(
        project_service_id=project_service_id,
        agreed_amount=project_service.agreed_amount,
        total_paid=total_paid,
        remaining=project_service.agreed_amount - total_paid,
        total_remunerated=total_remunerated,
    )
