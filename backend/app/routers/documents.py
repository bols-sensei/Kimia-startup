import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import require_roles
from app.core.ws_manager import manager
from app.database import get_db
from app.models import Document, User
from app.schemas.workflow import DocumentRead

router = APIRouter()

STORAGE_ROOT = Path("storage/documents")
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


@router.get("", response_model=list[DocumentRead])
def list_documents(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("CEO", "DA", "CM")),
):
    return db.query(Document).filter(Document.project_id == project_id).all()


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("CEO", "DA", "CM")),
):
    contents = await file.read()
    if len(contents) > settings.max_document_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.max_document_size_mb} Mo)",
        )

    stored_name = f"{uuid.uuid4().hex}_{file.filename}"
    dest_path = STORAGE_ROOT / stored_name
    with open(dest_path, "wb") as out:
        out.write(contents)

    document = Document(
        project_id=project_id,
        uploaded_by=current_user.id,
        name=file.filename,
        path=str(dest_path),
        mime_type=file.content_type or "application/octet-stream",
        size=len(contents),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    manager.broadcast_sync({"type": "document.created", "data": {"id": document.id, "project_id": project_id}})
    return document


@router.get("/{document_id}/download")
def download_document(
    document_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("CEO", "DA", "CM"))
):
    document = db.get(Document, document_id)
    if document is None or not Path(document.path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")
    return FileResponse(document.path, filename=document.name, media_type=document.mime_type)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("CEO", "DA"))
):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")
    Path(document.path).unlink(missing_ok=True)
    db.delete(document)
    db.commit()
