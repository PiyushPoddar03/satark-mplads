"""Alert and audit routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin_or_officer
from app.core.database import get_db
from app.models.enums import AlertSeverity, AlertStatus, AlertType, UserRole
from app.models.models import Alert, AuditLog, Project, ProjectEvent, RiskScore, User
from app.services.audit import log_audit

router = APIRouter(tags=["alerts-audit"])


# ── Alert Schemas ───────────────────────────────────────────────────

class AlertResponse(BaseModel):
    id: str
    alert_code: str
    project_id: str
    project_code: str | None = None
    alert_type: str
    severity: str
    title: str
    description: str | None = None
    evidence_data: dict | None = None
    status: str
    assigned_to: str | None = None
    resolution_notes: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class AlertUpdateRequest(BaseModel):
    status: AlertStatus | None = None
    assigned_to: str | None = None
    resolution_notes: str | None = None


class AuditLogResponse(BaseModel):
    id: str
    actor_id: str | None = None
    actor_role: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    description: str | None = None
    previous_value: dict | None = None
    new_value: dict | None = None
    created_at: str

    model_config = {"from_attributes": True}


class ProjectEventResponse(BaseModel):
    id: str
    project_id: str
    event_type: str
    title: str
    description: str | None = None
    metadata: dict | None = None
    actor_id: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    completed_projects: int
    critical_risk_projects: int
    high_risk_projects: int
    medium_risk_projects: int
    low_risk_projects: int
    critical_alerts: int
    pending_inspections: int
    total_inspectors: int
    total_evidence: int


# ── Alert Routes ────────────────────────────────────────────────────

alerts_router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@alerts_router.get("", response_model=list[AlertResponse])
async def list_alerts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    severity: AlertSeverity | None = None,
    alert_status: AlertStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(Alert).order_by(Alert.created_at.desc())

    if severity:
        query = query.where(Alert.severity == severity)
    if alert_status:
        query = query.where(Alert.status == alert_status)

    # Inspector only sees alerts for their projects
    if current_user.role == UserRole.FIELD_INSPECTOR:
        from app.models.enums import AssignmentStatus
        from app.models.models import ProjectInspector
        assigned_ids = select(ProjectInspector.project_id).where(
            ProjectInspector.inspector_user_id == current_user.id,
            ProjectInspector.status == AssignmentStatus.ACTIVE,
        )
        query = query.where(Alert.project_id.in_(assigned_ids))

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    alerts = result.scalars().all()

    responses = []
    for a in alerts:
        proj = await db.execute(select(Project).where(Project.id == a.project_id))
        project = proj.scalar_one_or_none()
        responses.append(AlertResponse(
            id=str(a.id),
            alert_code=a.alert_code,
            project_id=str(a.project_id),
            project_code=project.project_code if project else None,
            alert_type=a.alert_type.value,
            severity=a.severity.value,
            title=a.title,
            description=a.description,
            evidence_data=a.evidence_data,
            status=a.status.value,
            assigned_to=str(a.assigned_to) if a.assigned_to else None,
            resolution_notes=a.resolution_notes,
            created_at=a.created_at.isoformat(),
            updated_at=a.updated_at.isoformat(),
        ))
    return responses


@alerts_router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    body: AlertUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin_or_officer)],
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(alert, field, value)

    await log_audit(
        db, actor=current_user, action="update_alert",
        entity_type="alert", entity_id=str(alert.id),
        new_value=updates,
    )

    proj = await db.execute(select(Project).where(Project.id == alert.project_id))
    project = proj.scalar_one_or_none()

    return AlertResponse(
        id=str(alert.id),
        alert_code=alert.alert_code,
        project_id=str(alert.project_id),
        project_code=project.project_code if project else None,
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        title=alert.title,
        description=alert.description,
        evidence_data=alert.evidence_data,
        status=alert.status.value,
        assigned_to=str(alert.assigned_to) if alert.assigned_to else None,
        resolution_notes=alert.resolution_notes,
        created_at=alert.created_at.isoformat(),
        updated_at=alert.updated_at.isoformat(),
    )


# ── Audit Routes ────────────────────────────────────────────────────

audit_router = APIRouter(prefix="/api/audit", tags=["audit"])


@audit_router.get("", response_model=list[AuditLogResponse])
async def list_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    action: str | None = None,
    entity_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.AUDITOR):
        raise HTTPException(status_code=403, detail="Audit logs require admin or auditor role")

    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        AuditLogResponse(
            id=str(log.id),
            actor_id=str(log.actor_id) if log.actor_id else None,
            actor_role=log.actor_role,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            description=log.description,
            previous_value=log.previous_value,
            new_value=log.new_value,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]


# ── Project Timeline ───────────────────────────────────────────────

timeline_router = APIRouter(prefix="/api/timeline", tags=["timeline"])


@timeline_router.get("/{project_id}", response_model=list[ProjectEventResponse])
async def get_project_timeline(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    from app.api.deps import verify_inspector_project_access
    await verify_inspector_project_access(project_id, current_user, db)

    result = await db.execute(
        select(ProjectEvent)
        .where(ProjectEvent.project_id == project_id)
        .order_by(ProjectEvent.created_at.desc())
    )
    events = result.scalars().all()

    return [
        ProjectEventResponse(
            id=str(e.id),
            project_id=str(e.project_id),
            event_type=e.event_type,
            title=e.title,
            description=e.description,
            metadata=e.metadata_,
            actor_id=str(e.actor_id) if e.actor_id else None,
            created_at=e.created_at.isoformat(),
        )
        for e in events
    ]


# ── Dashboard Stats ────────────────────────────────────────────────

dashboard_router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@dashboard_router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    from app.models.enums import ProjectStatus, AssignmentStatus
    from app.models.models import Evidence, Inspection, ProjectInspector

    # Base query for projects based on role
    base_project_filter = Project.is_deleted == False

    # INSPECTOR: Only count assigned projects
    if current_user.role == UserRole.FIELD_INSPECTOR:
        assigned_project_ids = select(ProjectInspector.project_id).where(
            ProjectInspector.inspector_user_id == current_user.id,
            ProjectInspector.status == AssignmentStatus.ACTIVE,
        )
        project_filter = and_(base_project_filter, Project.id.in_(assigned_project_ids))

    # DISTRICT OFFICER: Only projects in their district
    elif current_user.role == UserRole.DISTRICT_OFFICER and current_user.district:
        project_filter = and_(base_project_filter, Project.district == current_user.district)

    # ADMIN/AUDITOR: All projects
    else:
        project_filter = base_project_filter

    # Fetch all scoped projects to calculate exact stats & risk distributions
    proj_results = await db.execute(select(Project).where(project_filter))
    scoped_projects = proj_results.scalars().all()

    total = len(scoped_projects)

    # Active projects: ongoing execution and NOT marked as completed/closed
    active = len([
        p for p in scoped_projects
        if p.status not in (ProjectStatus.COMPLETED, ProjectStatus.CLOSED)
    ])

    # Completed projects
    completed = len([
        p for p in scoped_projects
        if p.status in (ProjectStatus.COMPLETED, ProjectStatus.CLOSED)
    ])

    # Calculate project risk distribution based on latest RiskScore
    critical_risk_count = 0  # > 80%
    high_risk_count = 0      # > 60% and <= 80%
    medium_risk_count = 0    # >= 50% and <= 60%
    low_risk_count = 0       # < 50%

    for p in scoped_projects:
        rs_result = await db.execute(
            select(RiskScore)
            .where(RiskScore.project_id == p.id)
            .order_by(RiskScore.calculated_at.desc())
            .limit(1)
        )
        rs = rs_result.scalar_one_or_none()
        score = rs.overall_score if rs else 0.0

        if score > 80:
            critical_risk_count += 1
        elif score > 60:
            high_risk_count += 1
        elif score >= 50:
            medium_risk_count += 1
        else:
            low_risk_count += 1

    # Critical alerts (scoped by role - inspectors only see alerts for their projects)
    if current_user.role == UserRole.FIELD_INSPECTOR:
        alert_project_ids = select(ProjectInspector.project_id).where(
            ProjectInspector.inspector_user_id == current_user.id,
            ProjectInspector.status == AssignmentStatus.ACTIVE,
        )
        critical_alerts = (await db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.severity == AlertSeverity.CRITICAL,
                Alert.status == AlertStatus.OPEN,
                Alert.project_id.in_(alert_project_ids),
            )
        )).scalar() or 0
    elif current_user.role == UserRole.DISTRICT_OFFICER and current_user.district:
        # Officer sees alerts for projects in their district
        district_project_ids = select(Project.id).where(
            Project.district == current_user.district,
            Project.is_deleted == False,
        )
        critical_alerts = (await db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.severity == AlertSeverity.CRITICAL,
                Alert.status == AlertStatus.OPEN,
                Alert.project_id.in_(district_project_ids),
            )
        )).scalar() or 0
    else:
        # Admin/Auditor see all critical alerts
        critical_alerts = (await db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.severity == AlertSeverity.CRITICAL,
                Alert.status == AlertStatus.OPEN,
            )
        )).scalar() or 0

    # Pending inspections (scoped by role)
    pending = (await db.execute(
        select(func.count()).select_from(Project).where(
            and_(
                project_filter,
                Project.status == ProjectStatus.INSPECTION_PENDING,
            )
        )
    )).scalar() or 0

    # Total inspectors (everyone sees same count)
    inspectors = (await db.execute(
        select(func.count()).select_from(User).where(
            User.role == UserRole.FIELD_INSPECTOR, User.is_active == True
        )
    )).scalar() or 0

    # Evidence count (scoped by role - inspectors only see evidence from their projects)
    if current_user.role == UserRole.FIELD_INSPECTOR:
        assigned_project_ids_list = select(ProjectInspector.project_id).where(
            ProjectInspector.inspector_user_id == current_user.id,
            ProjectInspector.status == AssignmentStatus.ACTIVE,
        )
        evidence_count = (await db.execute(
            select(func.count()).select_from(Evidence)
            .join(Inspection, Evidence.inspection_id == Inspection.id)
            .where(Inspection.project_id.in_(assigned_project_ids_list))
        )).scalar() or 0
    elif current_user.role == UserRole.DISTRICT_OFFICER and current_user.district:
        district_project_ids_list = select(Project.id).where(
            Project.district == current_user.district,
            Project.is_deleted == False,
        )
        evidence_count = (await db.execute(
            select(func.count()).select_from(Evidence)
            .join(Inspection, Evidence.inspection_id == Inspection.id)
            .where(Inspection.project_id.in_(district_project_ids_list))
        )).scalar() or 0
    else:
        # Admin/Auditor see all evidence
        evidence_count = (await db.execute(select(func.count()).select_from(Evidence))).scalar() or 0

    return DashboardStats(
        total_projects=total,
        active_projects=active,
        completed_projects=completed,
        critical_risk_projects=critical_risk_count,
        high_risk_projects=high_risk_count,
        medium_risk_projects=medium_risk_count,
        low_risk_projects=low_risk_count,
        critical_alerts=critical_alerts,
        pending_inspections=pending,
        total_inspectors=inspectors,
        total_evidence=evidence_count,
    )
