from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.database import get_db
from app.models import Client, User
from app.schemas.business import ClientCreate, ClientRead, ClientUpdate

router = APIRouter()


@router.get("", response_model=list[ClientRead])
def list_clients(db: Session = Depends(get_db), _: User = Depends(require_permission("clients.view"))):
    return db.query(Client).order_by(Client.name).all()


@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("clients.view"))
):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable")
    return client


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate, db: Session = Depends(get_db), _: User = Depends(require_permission("clients.manage"))
):
    client = Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.patch("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("clients.manage")),
):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client introuvable")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)

    db.add(client)
    db.commit()
    db.refresh(client)
    return client
