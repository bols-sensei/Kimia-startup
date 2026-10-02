"""
Réalisations (portfolio) — CRUD réservé au CEO/DA.
Les images sont stockées dans storage/portfolio/.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.uploads import IMAGE_TYPES, sniff_ok
from app.core.deps import require_permission
from app.core.ws_manager import manager
from app.database import get_db
from app.models import PortfolioItem, User
from app.schemas.content import (
    PortfolioItemCreate,
    PortfolioItemRead,
    PortfolioItemUpdate,
)

router = APIRouter()

STORAGE_ROOT = Path("storage/portfolio")
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

MAX_IMAGE_MB = 10


@router.get("", response_model=list[PortfolioItemRead])
def list_items(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("portfolio.view")),
):
    return (
        db.query(PortfolioItem)
        .order_by(PortfolioItem.display_order, PortfolioItem.created_at.desc())
        .all()
    )


@router.post("", response_model=PortfolioItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: PortfolioItemCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("portfolio.manage")),
):
    item = PortfolioItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    manager.broadcast_sync({"type": "portfolio.created", "data": {"id": item.id}})
    return item


@router.patch("/{item_id}", response_model=PortfolioItemRead)
def update_item(
    item_id: int,
    payload: PortfolioItemUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("portfolio.manage")),
):
    item = db.get(PortfolioItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réalisation introuvable")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.add(item)
    db.commit()
    db.refresh(item)
    manager.broadcast_sync({"type": "portfolio.updated", "data": {"id": item.id}})
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("portfolio.manage")),
):
    item = db.get(PortfolioItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réalisation introuvable")

    # Supprimer l'image associée si elle existe
    if item.image_path:
        img = Path(item.image_path.lstrip("/"))
        if img.exists() and STORAGE_ROOT in img.parents:
            img.unlink(missing_ok=True)

    db.delete(item)
    db.commit()
    manager.broadcast_sync({"type": "portfolio.deleted", "data": {"id": item_id}})


@router.post("/upload", response_model=dict)
async def upload_image(
    file: UploadFile = File(...),
    _: User = Depends(require_permission("portfolio.manage")),
):
    """Upload d'une image de réalisation. Retourne le chemin public."""
    contents = await file.read()
    if len(contents) > MAX_IMAGE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image trop volumineuse (max {MAX_IMAGE_MB} Mo)",
        )

    ext = IMAGE_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format d'image non supporté (JPEG, PNG, WebP, GIF)",
        )
    if not sniff_ok(ext, contents[:16]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le contenu ne correspond pas au format déclaré",
        )

    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = STORAGE_ROOT / stored_name

    with open(dest_path, "wb") as out:
        out.write(contents)

    return {
        "image_path": f"/storage/portfolio/{stored_name}",
        "filename": file.filename,
        "size": len(contents),
    }