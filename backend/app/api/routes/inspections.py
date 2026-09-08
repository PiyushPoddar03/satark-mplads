"""Inspection and evidence routes."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_inspector_project_access
from app.core.config import get_settings
from app.core.database import get_db
from app.models.enums import (
    AssignmentStatus,
    EvidenceStatus,
    InspectionStatus,
    ProjectStatus,
    UserRole,
)
from app.models.models import (
    Evidence,
    Inspection,
    Project,
    ProjectEvent,
    ProjectInspector,
    User,
)
from app.services.ai import analyze_project_evidence, evaluate_project_risk
from app.services.audit import log_audit
from app.utils.geo import is_within_geofence

settings = get_settings()

router = APIRouter(prefix="/api/inspections", tags=["inspections"])


# ── Schemas ─────────────────────────────────────────────────────────

class StartInspectionRequest(BaseModel):
    project_id: str
    latitude: float
    longitude: float
    gps_accuracy: float | None = None


class InspectionResponse(BaseModel):
    id: str
    project_id: str
    inspector_user_id: str
    started_at: str
    submitted_at: str | None = None
    status: str
    notes: str | None = None
    start_latitude: float | None = None
    start_longitude: float | None = None
    start_gps_accuracy: float | None = None
    evidence_count: int = 0

    model_config = {"from_attributes": True}


class EvidenceResponse(BaseModel):
    id: str
    evidence_code: str
    project_id: str
    inspection_id: str
    capture_timestamp: str
    capture_latitude: float
    capture_longitude: float
    gps_accuracy: float | None = None
    distance_from_project: float | None = None
    is_within_geofence: bool | None = None
    sha256_hash: str
    status: str
    file_name: str
    storage_key: str
    created_at: str

    model_config = {"from_attributes": True}


class SubmitInspectionRequest(BaseModel):
    notes: str | None = None


# ── Routes ──────────────────────────────────────────────────────────

@router.post("/start", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
async def start_inspection(
    body: StartInspectionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Start a new inspection — inspector must be assigned to the project or be admin."""
    if current_user.role not in (UserRole.FIELD_INSPECTOR, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only inspectors or admins can start inspections")

    # Validate project
    proj_result = await db.execute(
        select(Project).where(Project.id == body.project_id, Project.is_deleted == False)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Server-side authorization
    await verify_inspector_project_access(body.project_id, current_user, db)

    inspection = Inspection(
        project_id=project.id,
        inspector_user_id=current_user.id,
        start_latitude=body.latitude,
        start_longitude=body.longitude,
        start_gps_accuracy=body.gps_accuracy,
    )
    db.add(inspection)
    await db.flush()

    # Update project status
    project.status = ProjectStatus.UNDER_INSPECTION

    db.add(ProjectEvent(
        project_id=project.id,
        event_type="inspection_started",
        title="Inspection Started",
        description=f"Inspection started by {current_user.full_name} at ({body.latitude:.4f}, {body.longitude:.4f})",
        actor_id=current_user.id,
        metadata_={"inspection_id": str(inspection.id)},
    ))

    await log_audit(
        db, actor=current_user, action="start_inspection",
        entity_type="inspection", entity_id=str(inspection.id),
    )

    return InspectionResponse(
        id=str(inspection.id),
        project_id=str(inspection.project_id),
        inspector_user_id=str(inspection.inspector_user_id),
        started_at=inspection.started_at.isoformat(),
        status=inspection.status.value,
        start_latitude=inspection.start_latitude,
        start_longitude=inspection.start_longitude,
        start_gps_accuracy=inspection.start_gps_accuracy,
    )


@router.post("/{inspection_id}/evidence", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    inspection_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    capture_timestamp: str | None = Form(None),
    latitude: float | None = Form(None),
    capture_latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    capture_longitude: float | None = Form(None),
    gps_accuracy: float | None = Form(None),
    sha256_hash: str | None = Form(None),
    device_info: str | None = Form(None),
):
    """Upload evidence for an active inspection with GPS validation and SHA-256 integrity."""
    # Validate inspection
    insp_result = await db.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    )
    inspection = insp_result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    if current_user.role == UserRole.FIELD_INSPECTOR and inspection.inspector_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized for this inspection")

    if inspection.status not in (InspectionStatus.STARTED, InspectionStatus.EVIDENCE_COLLECTED):
        raise HTTPException(status_code=400, detail="Inspection is not in a state to accept evidence")

    # Get project for geofence check
    proj_result = await db.execute(select(Project).where(Project.id == inspection.project_id))
    project = proj_result.scalar_one()

    # Resolve coordinates
    resolved_lat = latitude if latitude is not None else (capture_latitude if capture_latitude is not None else project.latitude)
    resolved_lng = longitude if longitude is not None else (capture_longitude if capture_longitude is not None else project.longitude)

    # Geofence validation
    within_fence, distance = is_within_geofence(
        resolved_lat, resolved_lng,
        project.latitude, project.longitude,
        project.inspection_radius_m,
    )

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "image/jpg", "application/octet-stream"}
    if file.content_type and file.content_type not in allowed_types:
        # Fall back if browser sent generic or jpg
        if not (file.filename and any(file.filename.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"])):
            raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")

    # Read file content
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:  # 25 MB limit
        raise HTTPException(status_code=400, detail="File size exceeds 25 MB limit")

    # SHA-256 hash
    file_hash = hashlib.sha256(content).hexdigest()

    # Generate evidence code
    evidence_code = f"EVD-{uuid.uuid4().hex[:8].upper()}"

    # Store file
    storage_dir = settings.evidence_storage / str(project.id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = f"{evidence_code}_{file.filename or 'evidence.jpg'}"
    storage_key = f"{project.id}/{safe_filename}"
    file_path = settings.evidence_storage / storage_key
    with open(file_path, "wb") as f:
        f.write(content)

    # Parse capture timestamp
    if capture_timestamp:
        try:
            cap_ts = datetime.fromisoformat(capture_timestamp)
        except ValueError:
            cap_ts = datetime.now(timezone.utc)
    else:
        cap_ts = datetime.now(timezone.utc)

    evidence = Evidence(
        evidence_code=evidence_code,
        project_id=project.id,
        inspection_id=inspection.id,
        inspector_user_id=current_user.id,
        storage_key=storage_key,
        file_name=safe_filename,
        file_size=len(content),
        mime_type=file.content_type or "image/jpeg",
        sha256_hash=file_hash,
        capture_timestamp=cap_ts,
        capture_latitude=resolved_lat,
        capture_longitude=resolved_lng,
        gps_accuracy=gps_accuracy,
        distance_from_project=distance,
        is_within_geofence=within_fence,
        status=EvidenceStatus.CAPTURED if within_fence else EvidenceStatus.FLAGGED,
        device_info={"raw": device_info} if device_info else None,
    )
    db.add(evidence)
    await db.flush()

    inspection.status = InspectionStatus.EVIDENCE_COLLECTED

    db.add(ProjectEvent(
        project_id=project.id,
        event_type="evidence_captured",
        title="Evidence Captured",
        description=f"Evidence {evidence_code} captured. Distance: {distance}m. Geofence: {'PASS' if within_fence else 'FAIL'}",
        actor_id=current_user.id,
        metadata_={"evidence_id": str(evidence.id), "within_geofence": within_fence, "distance": distance},
    ))

    await log_audit(
        db, actor=current_user, action="capture_evidence",
        entity_type="evidence", entity_id=str(evidence.id),
        new_value={"hash": file_hash, "geofence": within_fence, "distance": distance},
    )

    return EvidenceResponse(
        id=str(evidence.id),
        evidence_code=evidence.evidence_code,
        project_id=str(evidence.project_id),
        inspection_id=str(evidence.inspection_id),
        capture_timestamp=evidence.capture_timestamp.isoformat(),
        capture_latitude=evidence.capture_latitude,
        capture_longitude=evidence.capture_longitude,
        gps_accuracy=evidence.gps_accuracy,
        distance_from_project=evidence.distance_from_project,
        is_within_geofence=evidence.is_within_geofence,
        sha256_hash=evidence.sha256_hash,
        status=evidence.status.value,
        file_name=evidence.file_name,
        storage_key=evidence.storage_key,
        created_at=evidence.created_at.isoformat(),
    )


@router.post("/{inspection_id}/submit", response_model=InspectionResponse)
async def submit_inspection(
    inspection_id: str,
    body: SubmitInspectionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Submit an inspection for review and automatically trigger AI forensics & risk evaluation."""
    insp_result = await db.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    )
    inspection = insp_result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    if current_user.role == UserRole.FIELD_INSPECTOR and inspection.inspector_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized for this inspection")

    if inspection.status not in (InspectionStatus.STARTED, InspectionStatus.EVIDENCE_COLLECTED):
        raise HTTPException(status_code=400, detail="Inspection cannot be submitted in current state")

    inspection.status = InspectionStatus.SUBMITTED
    inspection.submitted_at = datetime.now(timezone.utc)
    inspection.notes = body.notes

    # Update project status
    proj_result = await db.execute(select(Project).where(Project.id == inspection.project_id))
    project = proj_result.scalar_one()
    project.status = ProjectStatus.UNDER_REVIEW

    db.add(ProjectEvent(
        project_id=project.id,
        event_type="inspection_submitted",
        title="Inspection Submitted",
        description=f"Inspection submitted by {current_user.full_name}",
        actor_id=current_user.id,
    ))

    await log_audit(
        db, actor=current_user, action="submit_inspection",
        entity_type="inspection", entity_id=str(inspection.id),
    )

    # Count evidence
    ev_result = await db.execute(select(Evidence).where(Evidence.inspection_id == inspection.id))
    evidence_items = ev_result.scalars().all()
    evidence_count = len(evidence_items)

    # Automatically analyze captured evidence with AI forensics and evaluate risk
    for ev in evidence_items:
        try:
            await analyze_project_evidence(ev, project, db)
        except Exception:
            pass

    try:
        await evaluate_project_risk(str(project.id), db)
    except Exception:
        pass

    return InspectionResponse(
        id=str(inspection.id),
        project_id=str(inspection.project_id),
        inspector_user_id=str(inspection.inspector_user_id),
        started_at=inspection.started_at.isoformat(),
        submitted_at=inspection.submitted_at.isoformat() if inspection.submitted_at else None,
        status=inspection.status.value,
        notes=inspection.notes,
        start_latitude=inspection.start_latitude,
        start_longitude=inspection.start_longitude,
        start_gps_accuracy=inspection.start_gps_accuracy,
        evidence_count=evidence_count,
    )


@router.get("/project/{project_id}", response_model=list[InspectionResponse])
async def get_project_inspections(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get all inspections for a project (respects access control)."""
    await verify_inspector_project_access(project_id, current_user, db)

    result = await db.execute(
        select(Inspection)
        .where(Inspection.project_id == project_id)
        .order_by(Inspection.started_at.desc())
    )
    inspections = result.scalars().all()

    responses = []
    for insp in inspections:
        ev_result = await db.execute(select(Evidence).where(Evidence.inspection_id == insp.id))
        ev_count = len(ev_result.scalars().all())
        responses.append(InspectionResponse(
            id=str(insp.id),
            project_id=str(insp.project_id),
            inspector_user_id=str(insp.inspector_user_id),
            started_at=insp.started_at.isoformat(),
            submitted_at=insp.submitted_at.isoformat() if insp.submitted_at else None,
            status=insp.status.value,
            notes=insp.notes,
            start_latitude=insp.start_latitude,
            start_longitude=insp.start_longitude,
            start_gps_accuracy=insp.start_gps_accuracy,
            evidence_count=ev_count,
        ))
    return responses


@router.get("/{inspection_id}/evidence", response_model=list[EvidenceResponse])
async def get_inspection_evidence(
    inspection_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get all evidence for an inspection."""
    insp_result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = insp_result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    await verify_inspector_project_access(str(inspection.project_id), current_user, db)

    result = await db.execute(
        select(Evidence).where(Evidence.inspection_id == inspection_id).order_by(Evidence.created_at.desc())
    )
    items = result.scalars().all()

    return [
        EvidenceResponse(
            id=str(e.id),
            evidence_code=e.evidence_code,
            project_id=str(e.project_id),
            inspection_id=str(e.inspection_id),
            capture_timestamp=e.capture_timestamp.isoformat(),
            capture_latitude=e.capture_latitude,
            capture_longitude=e.capture_longitude,
            gps_accuracy=e.gps_accuracy,
            distance_from_project=e.distance_from_project,
            is_within_geofence=e.is_within_geofence,
            sha256_hash=e.sha256_hash,
            status=e.status.value,
            file_name=e.file_name,
            storage_key=e.storage_key,
            created_at=e.created_at.isoformat(),
        )
        for e in items
    ]


@router.get("/evidence-file/{storage_key:path}")
async def get_evidence_file(storage_key: str):
    """Serve stored inspection evidence image with appropriate content type."""
    file_path = (settings.evidence_storage / storage_key).resolve()

    # Security check: ensure path is within evidence_storage
    try:
        file_path.relative_to(settings.evidence_storage.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Evidence file not found")

    suffix = file_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".heic": "image/heic",
        ".heif": "image/heif",
    }
    media_type = media_types.get(suffix, "image/jpeg")
    return FileResponse(path=str(file_path), media_type=media_type)

