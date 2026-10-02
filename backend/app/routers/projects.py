from sqlalchemy.orm import Session, selectinload
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import require_any_permission, require_permission, user_can
from app.core.ws_manager import manager

from app.database import get_db
from app.models import Activity, ActivityAssignment, Channel, ChannelType, Project, User
from app.schemas.workflow import ProjectCreate, ProjectDetailRead, ProjectRead, ProjectUpdate
from app.services.project_service import create_project as create_project_service

router = APIRouter()


@router.get("", response_model=list[ProjectRead])
def list_projects(
    responsible_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_permission("projects.view", "projects.view_assigned")),
):
    query = db.query(Project)
    # CM : uniquement les projets où il est assigné à au moins une activité
    # (§18 : pas de liste globale des clients/projets pour ce rôle).
    if not user_can(current_user, "projects.view"):
        query = (
            query.join(Activity, Activity.project_id == Project.id)
            .join(ActivityAssignment, ActivityAssignment.activity_id == Activity.id)
            .filter(ActivityAssignment.user_id == current_user.id)
            .distinct()
        )
    if responsible_id is not None:
        query = query.filter(Project.responsible_id == responsible_id)
    return query.order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectDetailRead)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("projects.view", "projects.view_assigned")),
):
    project = (
        db.query(Project)
        .options(selectinload(Project.project_services))
        .filter(Project.id == project_id)
        .one_or_none()
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable")
    return project


@router.post("", response_model=ProjectDetailRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("projects.manage")),
):
    project = create_project_service(db, payload)
    
    # Créer automatiquement le canal de discussion du projet
    channel = Channel(
        name=f"Projet · {project.name}",
        type=ChannelType.PROJECT,
        project_id=project.id,
    )
    db.add(channel)
    db.commit()
    
    manager.broadcast_sync({"type": "project.created", "data": {"id": project.id}})
    return project

@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("projects.manage")),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    db.add(project)
    db.commit()
    db.refresh(project)

    manager.broadcast_sync({"type": "project.updated", "data": {"id": project.id}})
    return project
