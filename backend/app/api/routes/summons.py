"""Inspector summons routes - District Officer requests detailed reports from inspectors."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enums import SummonsStatus, UserRole
from app.models.models import InspectorSummons, Project, ProjectEvent, ProjectInspector, User
from app.schemas.summons import SummonsCreate, SummonsItem, SummonsResponse, SummonsReview
from app.services.audit import log_audit

router = APIRouter(prefix="/api/summons", tags=["summons"])


async def _build_summons_response(summons: InspectorSummons, db: AsyncSession) -> SummonsItem:
    """Build full summons response with project and user details."""
    # Get project
    project_result = await db.execute(select(Project).where(Project.id == summons.project_id))
    project = project_result.scalar_one_or_none()

    # Get inspector
    inspector_result = await db.execute(select(User).where(User.id == summons.inspector_user_id))
    inspector = inspector_result.scalar_one_or_none()

    # Get officer
    officer_result = await db.execute(select(User).where(User.id == summons.officer_user_id))
    officer = officer_result.scalar_one_or_none()

    return SummonsItem(
        id=str(summons.id),
        summons_code=summons.summons_code,
        project_id=str(summons.project_id),
        project_code=project.project_code if project else None,
        project_name=project.name if project else None,
        inspector_user_id=str(summons.inspector_user_id),
        inspector_name=inspector.full_name if inspector else None,
        inspector_id=inspector.inspector_id if inspector else None,
        officer_user_id=str(summons.officer_user_id),
        officer_name=officer.full_name if officer else None,
        reason=summons.reason,
        questions=summons.questions,
        status=summons.status.value,
        response_text=summons.response_text,
        response_attachments=summons.response_attachments,
        responded_at=summons.responded_at.isoformat() if summons.responded_at else None,
        officer_notes=summons.officer_notes,
        reviewed_at=summons.reviewed_at.isoformat() if summons.reviewed_at else None,
        closed_at=summons.closed_at.isoformat() if summons.closed_at else None,
        created_at=summons.created_at.isoformat(),
        updated_at=summons.updated_at.isoformat(),
    )


@router.post("", response_model=SummonsItem)
async def create_summons(
    body: SummonsCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    District Officer or Admin creates a summons requesting detailed report from inspector.
    """
    if current_user.role not in (UserRole.DISTRICT_OFFICER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only district officers or admins can issue summons")

    # Verify project exists
    project_result = await db.execute(select(Project).where(Project.id == body.project_id, Project.is_deleted == False))
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role == UserRole.DISTRICT_OFFICER and current_user.district and project.district:
        if project.district.strip().lower() != current_user.district.strip().lower():
            raise HTTPException(status_code=403, detail="You can only issue summons for projects in your district")

    # Look up inspector by ID or inspector_id
    from app.models.enums import AssignmentStatus
    inspector = None
    if body.inspector_user_id:
        insp_res = await db.execute(
            select(User).where(
                (User.id == body.inspector_user_id) | (User.inspector_id == body.inspector_user_id),
                User.role == UserRole.FIELD_INSPECTOR,
            )
        )
        inspector = insp_res.scalar_one_or_none()

    # Fallback to active project assignment if inspector wasn't directly found
    if not inspector:
        assign_res = await db.execute(
            select(ProjectInspector).where(
                ProjectInspector.project_id == body.project_id,
                ProjectInspector.status == AssignmentStatus.ACTIVE,
            )
        )
        active_assign = assign_res.scalar_one_or_none()
        if active_assign:
            insp_res = await db.execute(select(User).where(User.id == active_assign.inspector_user_id))
            inspector = insp_res.scalar_one_or_none()

    if not inspector:
        raise HTTPException(status_code=400, detail="No active field inspector assigned to this project to receive summons")

    # Generate summons code
    import time
    district_prefix = project.district[:3].upper() if project.district else "PRJ"
    summons_code = f"SUMMONS-{district_prefix}-{int(time.time()) % 100000}"

    # Create summons
    summons = InspectorSummons(
        summons_code=summons_code,
        project_id=project.id,
        inspector_user_id=inspector.id,
        officer_user_id=current_user.id,
        reason=body.reason,
        questions=body.questions,
    )
    db.add(summons)
    await db.flush()

    # Log event
    db.add(ProjectEvent(
        project_id=project.id,
        event_type="summons_issued",
        title="Inspector Summons Issued",
        description=f"Administrative inquiry issued by {current_user.full_name} to Inspector {inspector.inspector_id or inspector.full_name}",
        actor_id=current_user.id,
        metadata_={"summons_id": str(summons.id), "summons_code": summons_code},
    ))

    await log_audit(
        db, actor=current_user, action="create_summons",
        entity_type="summons", entity_id=str(summons.id),
        new_value={"project_id": str(project.id), "inspector_id": str(inspector.id)},
    )

    return await _build_summons_response(summons, db)


@router.get("", response_model=list[SummonsItem])
async def list_summons(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status: SummonsStatus | None = None,
    project_id: str | None = None,
):
    """
    List summons:
    - District Officer: summons they issued or for projects in their district
    - Inspector: summons issued to them
    - Admin/Auditor: all summons
    """
    query = select(InspectorSummons)

    if current_user.role == UserRole.FIELD_INSPECTOR:
        query = query.where(InspectorSummons.inspector_user_id == current_user.id)
    elif current_user.role == UserRole.DISTRICT_OFFICER:
        if current_user.district:
            district_projects = select(Project.id).where(
                func.lower(Project.district) == current_user.district.lower(),
                Project.is_deleted == False,
            )
            query = query.where(
                (InspectorSummons.officer_user_id == current_user.id) |
                (InspectorSummons.project_id.in_(district_projects))
            )
        else:
            query = query.where(InspectorSummons.officer_user_id == current_user.id)
    # Admin and Auditor see all

    if status:
        query = query.where(InspectorSummons.status == status)
    if project_id:
        query = query.where(InspectorSummons.project_id == project_id)

    query = query.order_by(InspectorSummons.created_at.desc())
    result = await db.execute(query)
    summons_list = result.scalars().all()

    return [await _build_summons_response(s, db) for s in summons_list]


@router.get("/{summons_id}", response_model=SummonsItem)
async def get_summons(
    summons_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get single summons details."""
    result = await db.execute(select(InspectorSummons).where(InspectorSummons.id == summons_id))
    summons = result.scalar_one_or_none()
    if not summons:
        raise HTTPException(status_code=404, detail="Summons not found")

    # Authorization check
    if current_user.role == UserRole.FIELD_INSPECTOR and summons.inspector_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if current_user.role == UserRole.DISTRICT_OFFICER and summons.officer_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return await _build_summons_response(summons, db)


@router.post("/{summons_id}/respond", response_model=SummonsItem)
async def respond_to_summons(
    summons_id: str,
    body: SummonsResponse,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Inspector submits response to summons."""
    if current_user.role != UserRole.FIELD_INSPECTOR:
        raise HTTPException(status_code=403, detail="Only inspectors can respond to summons")

    result = await db.execute(select(InspectorSummons).where(InspectorSummons.id == summons_id))
    summons = result.scalar_one_or_none()
    if not summons:
        raise HTTPException(status_code=404, detail="Summons not found")

    if summons.inspector_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only respond to your own summons")

    if summons.status != SummonsStatus.PENDING:
        raise HTTPException(status_code=400, detail="Summons has already been responded to")

    from datetime import datetime, timezone
    summons.response_text = body.response_text
    summons.response_attachments = body.response_attachments
    summons.responded_at = datetime.now(timezone.utc)
    summons.status = SummonsStatus.RESPONDED

    # Log event
    db.add(ProjectEvent(
        project_id=summons.project_id,
        event_type="summons_responded",
        title="Inspector Submitted Summons Response",
        description=f"Inspector {current_user.inspector_id} submitted detailed report in response to summons {summons.summons_code}",
        actor_id=current_user.id,
        metadata_={"summons_id": str(summons.id)},
    ))

    await log_audit(
        db, actor=current_user, action="respond_summons",
        entity_type="summons", entity_id=str(summons.id),
    )

    return await _build_summons_response(summons, db)


@router.post("/{summons_id}/review", response_model=SummonsItem)
async def review_summons(
    summons_id: str,
    body: SummonsReview,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """District Officer or Admin reviews summons response and updates status."""
    if current_user.role not in (UserRole.DISTRICT_OFFICER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only district officers or administrators can review summons")

    result = await db.execute(select(InspectorSummons).where(InspectorSummons.id == summons_id))
    summons = result.scalar_one_or_none()
    if not summons:
        raise HTTPException(status_code=404, detail="Summons not found")

    if current_user.role == UserRole.DISTRICT_OFFICER and summons.officer_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only review your own summons")

    if summons.status == SummonsStatus.PENDING:
        raise HTTPException(status_code=400, detail="Inspector has not responded yet")

    from datetime import datetime, timezone
    summons.officer_notes = body.officer_notes
    summons.status = body.status

    if body.status == SummonsStatus.REVIEWED:
        summons.reviewed_at = datetime.now(timezone.utc)
    elif body.status == SummonsStatus.CLOSED:
        summons.closed_at = datetime.now(timezone.utc)

    # Log event
    db.add(ProjectEvent(
        project_id=summons.project_id,
        event_type="summons_reviewed",
        title="Summons Response Reviewed",
        description=f"District Officer reviewed summons {summons.summons_code} - Status: {body.status.value}",
        actor_id=current_user.id,
        metadata_={"summons_id": str(summons.id), "new_status": body.status.value},
    ))

    await log_audit(
        db, actor=current_user, action="review_summons",
        entity_type="summons", entity_id=str(summons.id),
        new_value={"status": body.status.value},
    )

    return await _build_summons_response(summons, db)
