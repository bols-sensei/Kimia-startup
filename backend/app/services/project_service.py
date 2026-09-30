"""
Logique "complexe touchant plusieurs modèles" (§6) : sortie du CRUD simple des
routers. Rassemble la création d'un projet, de ses prestations (ProjectService)
et la génération des activités/checklists depuis les ActivityTemplate associés
au service — sans jamais modifier les templates eux-mêmes (copie, §21).
"""

from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Activity,
    ActivityChecklist,
    ActivityPriority,
    ActivityTemplate,
    ChecklistTemplateItem,
    Project,
    ProjectService,
)
from app.schemas.workflow import ProjectCreate


def create_project(db: Session, data: ProjectCreate) -> Project:
    project = Project(
        client_id=data.client_id,
        request_id=data.request_id,
        name=data.name,
        description=data.description,
        project_type=data.project_type,
        category=data.category,
        responsible_id=data.responsible_id,
        start_date=data.start_date,
        planned_end_date=data.planned_end_date,
        event_date=data.event_date,
        event_time=data.event_time,
        event_location=data.event_location,
    )
    db.add(project)
    db.flush()  # obtenir project.id sans committer

    for service_in in data.services:
        project_service = ProjectService(
            project_id=project.id,
            service_id=service_in.service_id,
            agreed_amount=service_in.agreed_amount,
            currency=service_in.currency or settings.default_currency,
        )
        db.add(project_service)
        db.flush()

        _generate_activities_from_templates(db, project, project_service)

    db.commit()
    db.refresh(project)
    return project


def _generate_activities_from_templates(
    db: Session, project: Project, project_service: ProjectService
) -> None:
    templates = (
        db.query(ActivityTemplate)
        .filter(
            ActivityTemplate.service_id == project_service.service_id,
            ActivityTemplate.is_active.is_(True),
        )
        .order_by(ActivityTemplate.display_order)
        .all()
    )

    for template in templates:
        activity = Activity(
            project_id=project.id,
            project_service_id=project_service.id,
            template_id=template.id,
            required_skill_id=template.required_skill_id,
            name=template.name,
            description=template.description,
            priority=template.priority or ActivityPriority.NORMALE,
        )
        db.add(activity)
        db.flush()

        checklist_items = (
            db.query(ChecklistTemplateItem)
            .filter(ChecklistTemplateItem.activity_template_id == template.id)
            .order_by(ChecklistTemplateItem.display_order)
            .all()
        )
        for item in checklist_items:
            db.add(
                ActivityChecklist(
                    activity_id=activity.id,
                    label=item.label,
                    display_order=item.display_order,
                )
            )
