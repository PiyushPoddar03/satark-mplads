"""Inspector assignment routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin, require_admin_or_officer
from app.core.database import get_db
from app.models.enums import AssignmentStatus, ProjectStatus, UserRole
from app.models.models import Project, ProjectEvent, ProjectInspector, User
from app.services.audit import log_audit

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


class AssignInspectorRequest(BaseModel):
    project_id: str
    inspector_user_id: str


class AssignmentResponse(BaseModel):
    id: str
    project_id: str
    project_code: str
    project_name: str
    inspector_user_id: str
    inspector_id: str
    inspector_name: str
    assigned_at: str
    status: str

    model_config = {"from_attributes": True}


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def assign_inspector(
    body: AssignInspectorRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[User, Depends(require_admin_or_officer)],
):
    # Validate project
    proj_result = await db.execute(
        select(Project).where(Project.id == body.project_id, Project.is_deleted == False)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # If district officer, check district
    if actor.role == UserRole.DISTRICT_OFFICER and actor.district and project.district:
        if project.district.strip().lower() != actor.district.strip().lower():
            raise HTTPException(status_code=403, detail="You can only assign inspectors for projects in your district")

    # Validate inspector
    insp_result = await db.execute(
        select(User).where(
            User.id == body.inspector_user_id,
            User.role == UserRole.FIELD_INSPECTOR,
            User.is_active == True,
        )
    )
    inspector = insp_result.scalar_one_or_none()
    if not inspector:
        raise HTTPException(status_code=404, detail="Inspector not found or not an active field inspector")

    # Deactivate existing active assignments for this project
    existing = await db.execute(
        select(ProjectInspector).where(
            ProjectInspector.project_id == body.project_id,
            ProjectInspector.status == AssignmentStatus.ACTIVE,
        )
    )
    for old in existing.scalars().all():
        old.status = AssignmentStatus.REASSIGNED
        old.unassigned_at = datetime.now(timezone.utc)

    # Create new assignment
    assignment = ProjectInspector(
        project_id=project.id,
        inspector_user_id=inspector.id,
        assigned_by=actor.id,
    )
    db.add(assignment)
    await db.flush()

    # Update project status
    if project.status not in (ProjectStatus.UNDER_INSPECTION, ProjectStatus.UNDER_REVIEW):
        project.status = ProjectStatus.INSPECTOR_ASSIGNED

    # Timeline event
    db.add(ProjectEvent(
        project_id=project.id,
        event_type="inspector_assigned",
        title="Inspector Assigned",
        description=f"Inspector {inspector.inspector_id} ({inspector.full_name}) assigned by {actor.full_name}",
        actor_id=actor.id,
    ))

    await log_audit(
        db, actor=actor, action="assign_inspector",
        entity_type="project_inspector", entity_id=str(assignment.id),
        new_value={
            "project_id": str(project.id),
            "inspector_user_id": str(inspector.id),
            "inspector_id": inspector.inspector_id,
        },
    )

    return AssignmentResponse(
        id=str(assignment.id),
        project_id=str(project.id),
        project_code=project.project_code,
        project_name=project.name,
        inspector_user_id=str(inspector.id),
        inspector_id=inspector.inspector_id,
        inspector_name=inspector.full_name,
        assigned_at=assignment.assigned_at.isoformat(),
        status=assignment.status.value,
    )


@router.get("/project/{project_id}", response_model=list[AssignmentResponse])
async def get_project_assignments(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get assignment history for a project (accessible by authenticated users)."""
    result = await db.execute(
        select(ProjectInspector)
        .where(ProjectInspector.project_id == project_id)
        .order_by(ProjectInspector.assigned_at.desc())
    )
    assignments = result.scalars().all()

    responses = []
    for a in assignments:
        insp = await db.execute(select(User).where(User.id == a.inspector_user_id))
        inspector = insp.scalar_one_or_none()
        proj = await db.execute(select(Project).where(Project.id == a.project_id))
        project = proj.scalar_one_or_none()
        if inspector and project:
            responses.append(AssignmentResponse(
                id=str(a.id),
                project_id=str(a.project_id),
                project_code=project.project_code,
                project_name=project.name,
                inspector_user_id=str(inspector.id),
                inspector_id=inspector.inspector_id or "N/A",
                inspector_name=inspector.full_name,
                assigned_at=a.assigned_at.isoformat(),
                status=a.status.value,
            ))
    return responses


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_assignment(
    assignment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[User, Depends(require_admin_or_officer)],
):
    result = await db.execute(
        select(ProjectInspector).where(
            ProjectInspector.id == assignment_id,
            ProjectInspector.status == AssignmentStatus.ACTIVE,
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Active assignment not found")

    assignment.status = AssignmentStatus.REVOKED
    assignment.unassigned_at = datetime.now(timezone.utc)

    await log_audit(
        db, actor=admin, action="revoke_assignment",
        entity_type="project_inspector", entity_id=str(assignment.id),
    )
