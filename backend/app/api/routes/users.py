"""User management routes (Admin & District Officer Inspector Workflow)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin, require_admin_or_officer
from app.core.database import get_db
from app.core.security import hash_password
from app.models.enums import (
    AssignmentStatus,
    InspectorRequestStatus,
    InspectorRequestType,
    UserRole,
)
from app.models.models import (
    Alert,
    AuditLog,
    Evidence,
    EvidenceAnalysis,
    ExpenseBill,
    Inspection,
    InspectorRequest,
    InspectorSummons,
    Project,
    ProjectEvent,
    ProjectInspector,
    User,
)
from app.schemas.user import (
    InspectorRequestCreate,
    InspectorRequestResponse,
    InspectorRequestReview,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.audit import log_audit

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin_or_officer)],
    role: UserRole | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """List users. Admins can list all users; District Officers can list field inspectors."""
    query = select(User).where(User.is_active == True)
    if current_user.role == UserRole.DISTRICT_OFFICER:
        # District officers can inspect field inspectors in their district or generally
        query = query.where(User.role == UserRole.FIELD_INSPECTOR)
        if current_user.district:
            # If district set, prefer matching district or unassigned
            query = query.where(
                (User.district == current_user.district) | (User.district == None) | (User.district == "")
            )
    elif role:
        query = query.where(User.role == role)

    query = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()
    return [
        UserResponse(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            role=u.role.value,
            inspector_id=u.inspector_id,
            phone=u.phone,
            state=u.state,
            district=u.district,
            is_active=u.is_active,
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    """Directly create a user (Admin only)."""
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check inspector_id uniqueness
    if body.inspector_id:
        existing_insp = await db.execute(select(User).where(User.inspector_id == body.inspector_id))
        if existing_insp.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Inspector ID already in use")

    # Require inspector_id for inspectors
    if body.role == UserRole.FIELD_INSPECTOR and not body.inspector_id:
        raise HTTPException(status_code=400, detail="Inspector ID is required for field inspectors")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        inspector_id=body.inspector_id,
        phone=body.phone,
        state=body.state,
        district=body.district,
    )
    db.add(user)
    await db.flush()

    await log_audit(
        db, actor=admin, action="create_user",
        entity_type="user", entity_id=str(user.id),
        new_value={"email": body.email, "role": body.role.value, "inspector_id": body.inspector_id},
    )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        inspector_id=user.inspector_id,
        phone=user.phone,
        state=user.state,
        district=user.district,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    """Update user information (Admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)

    await log_audit(
        db, actor=admin, action="update_user",
        entity_type="user", entity_id=str(user.id),
        new_value=updates,
    )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        inspector_id=user.inspector_id,
        phone=user.phone,
        state=user.state,
        district=user.district,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


async def purge_user_and_all_data(user_id: str, db: AsyncSession) -> None:
    """
    Completely and permanently remove a user and all their associated records
    (evidence, analysis, inspections, bills, assignments, summons, event links) from the database.
    """
    # 1. EvidenceAnalysis records for evidence captured by this inspector
    ev_ids_res = await db.execute(
        select(Evidence.id).where(
            (Evidence.inspector_user_id == user_id) |
            (Evidence.inspection_id.in_(select(Inspection.id).where(Inspection.inspector_user_id == user_id)))
        )
    )
    ev_ids = [row[0] for row in ev_ids_res.all()]
    if ev_ids:
        await db.execute(delete(EvidenceAnalysis).where(EvidenceAnalysis.evidence_id.in_(ev_ids)))

    # 2. Evidence items
    await db.execute(
        delete(Evidence).where(
            (Evidence.inspector_user_id == user_id) |
            (Evidence.inspection_id.in_(select(Inspection.id).where(Inspection.inspector_user_id == user_id)))
        )
    )

    # 3. Inspections
    await db.execute(delete(Inspection).where(Inspection.inspector_user_id == user_id))

    # 4. Project assignments
    await db.execute(delete(ProjectInspector).where(ProjectInspector.inspector_user_id == user_id))
    await db.execute(
        update(ProjectInspector).where(ProjectInspector.assigned_by == user_id).values(assigned_by=None)
    )

    # 5. Inspector Summons
    await db.execute(
        delete(InspectorSummons).where(
            (InspectorSummons.inspector_user_id == user_id) | (InspectorSummons.officer_user_id == user_id)
        )
    )

    # 6. Expense Bills & Invoices
    await db.execute(delete(ExpenseBill).where(ExpenseBill.inspector_user_id == user_id))

    # 7. Unlink Alerts
    await db.execute(update(Alert).where(Alert.assigned_to == user_id).values(assigned_to=None))

    # 8. Unlink Project Events & Project creators
    await db.execute(update(ProjectEvent).where(ProjectEvent.actor_id == user_id).values(actor_id=None))
    await db.execute(update(Project).where(Project.created_by == user_id).values(created_by=None))

    # 9. Unlink Audit Logs
    await db.execute(update(AuditLog).where(AuditLog.actor_id == user_id).values(actor_id=None))

    # 10. Unlink Inspector Requests
    await db.execute(
        update(InspectorRequest).where(InspectorRequest.target_inspector_id == user_id).values(target_inspector_id=None)
    )
    await db.execute(
        update(InspectorRequest).where(InspectorRequest.reviewed_by == user_id).values(reviewed_by=None)
    )

    # 11. Delete the User record itself
    await db.execute(delete(User).where(User.id == user_id))
    await db.flush()


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    """Completely delete and purge an inspector or user and all associated database records (Admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")

    user_name = user.full_name
    user_email = user.email
    user_role = user.role.value

    # Permanently delete user and all associated records
    await purge_user_and_all_data(user_id, db)

    await log_audit(
        db, actor=admin, action="delete_user",
        entity_type="user", entity_id=user_id,
        previous_value={"email": user_email, "role": user_role, "full_name": user_name},
        new_value={"purged": True},
    )

    return {"message": f"User {user_name} ({user_email}) and all associated records have been permanently removed from the database"}


# ── Inspector Management Requests (District Officer <-> Admin Workflow) ─

@router.post("/inspector-requests", response_model=InspectorRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_inspector_request(
    body: InspectorRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin_or_officer)],
):
    """Submit a request to Add or Remove an inspector (District Officer -> Admin Approval)."""
    target_name = None
    if body.request_type == InspectorRequestType.REMOVE:
        if not body.target_inspector_id:
            raise HTTPException(status_code=400, detail="Target inspector ID is required for removal request")
        t_res = await db.execute(select(User).where(User.id == body.target_inspector_id))
        target_user = t_res.scalar_one_or_none()
        if not target_user:
            raise HTTPException(status_code=404, detail="Target inspector not found")
        target_name = target_user.full_name

    request_code = f"REQ-INSP-{uuid.uuid4().hex[:8].upper()}"

    req = InspectorRequest(
        request_code=request_code,
        request_type=body.request_type,
        officer_user_id=current_user.id,
        target_inspector_id=body.target_inspector_id,
        inspector_data=body.inspector_data,
        reason=body.reason,
        status=InspectorRequestStatus.PENDING,
    )
    db.add(req)
    await db.flush()

    await log_audit(
        db, actor=current_user, action="create_inspector_request",
        entity_type="inspector_request", entity_id=str(req.id),
        new_value={"request_code": request_code, "type": body.request_type.value, "reason": body.reason},
    )

    return InspectorRequestResponse(
        id=str(req.id),
        request_code=req.request_code,
        request_type=req.request_type.value,
        officer_user_id=str(req.officer_user_id),
        officer_name=current_user.full_name,
        target_inspector_id=str(req.target_inspector_id) if req.target_inspector_id else None,
        target_inspector_name=target_name,
        inspector_data=req.inspector_data,
        reason=req.reason,
        status=req.status.value,
        reviewed_by=None,
        reviewer_name=None,
        admin_notes=None,
        reviewed_at=None,
        created_at=req.created_at.isoformat(),
        updated_at=req.updated_at.isoformat(),
    )


@router.get("/inspector-requests", response_model=list[InspectorRequestResponse])
async def list_inspector_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin_or_officer)],
    status: InspectorRequestStatus | None = None,
):
    """List inspector requests. Admin sees all; District Officer sees their submitted requests."""
    query = select(InspectorRequest)
    if current_user.role == UserRole.DISTRICT_OFFICER:
        query = query.where(InspectorRequest.officer_user_id == current_user.id)

    if status:
        query = query.where(InspectorRequest.status == status)

    query = query.order_by(InspectorRequest.created_at.desc())
    result = await db.execute(query)
    requests = result.scalars().all()

    # Prefetch users for nice names
    user_ids = set()
    for r in requests:
        user_ids.add(r.officer_user_id)
        if r.target_inspector_id:
            user_ids.add(r.target_inspector_id)
        if r.reviewed_by:
            user_ids.add(r.reviewed_by)

    users_map = {}
    if user_ids:
        u_res = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in u_res.scalars().all():
            users_map[str(u.id)] = u.full_name

    return [
        InspectorRequestResponse(
            id=str(r.id),
            request_code=r.request_code,
            request_type=r.request_type.value,
            officer_user_id=str(r.officer_user_id),
            officer_name=users_map.get(str(r.officer_user_id)),
            target_inspector_id=str(r.target_inspector_id) if r.target_inspector_id else None,
            target_inspector_name=users_map.get(str(r.target_inspector_id)) if r.target_inspector_id else None,
            inspector_data=r.inspector_data,
            reason=r.reason,
            status=r.status.value,
            reviewed_by=str(r.reviewed_by) if r.reviewed_by else None,
            reviewer_name=users_map.get(str(r.reviewed_by)) if r.reviewed_by else None,
            admin_notes=r.admin_notes,
            reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else None,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in requests
    ]


@router.post("/inspector-requests/{request_id}/approve", response_model=InspectorRequestResponse)
async def approve_inspector_request(
    request_id: str,
    body: InspectorRequestReview,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    """Approve an inspector request (Admin only). Executes the ADD or REMOVE operation."""
    result = await db.execute(select(InspectorRequest).where(InspectorRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Inspector request not found")

    if req.status != InspectorRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request is already {req.status.value}")

    target_name = None

    if req.request_type == InspectorRequestType.ADD:
        data = req.inspector_data or {}
        email = data.get("email")
        inspector_id = data.get("inspector_id")
        full_name = data.get("full_name")
        password = data.get("password") or "Inspector@123"
        phone = data.get("phone")
        state = data.get("state")
        district = data.get("district")

        if not email or not full_name:
            raise HTTPException(status_code=400, detail="Missing required inspector details in request payload")

        # Check existing email
        ex_email = await db.execute(select(User).where(User.email == email))
        if ex_email.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"User with email '{email}' already exists")

        # Check existing inspector_id
        if inspector_id:
            ex_insp = await db.execute(select(User).where(User.inspector_id == inspector_id))
            if ex_insp.scalar_one_or_none():
                raise HTTPException(status_code=400, detail=f"Inspector ID '{inspector_id}' is already assigned")
        else:
            inspector_id = f"INS-{uuid.uuid4().hex[:6].upper()}"

        new_inspector = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=UserRole.FIELD_INSPECTOR,
            inspector_id=inspector_id,
            phone=phone,
            state=state,
            district=district,
            is_active=True,
        )
        db.add(new_inspector)
        await db.flush()

        req.target_inspector_id = new_inspector.id

    elif req.request_type == InspectorRequestType.REMOVE:
        if not req.target_inspector_id:
            raise HTTPException(status_code=400, detail="No target inspector ID attached to removal request")

        t_res = await db.execute(select(User).where(User.id == req.target_inspector_id))
        target_user = t_res.scalar_one_or_none()
        if target_user:
            target_name = target_user.full_name
            target_id = target_user.id
            # Permanently remove inspector and all associated records from database
            await purge_user_and_all_data(target_id, db)

    req.status = InspectorRequestStatus.APPROVED
    req.reviewed_by = admin.id
    req.admin_notes = body.admin_notes or "Approved by Admin"
    req.reviewed_at = datetime.now(timezone.utc)

    await log_audit(
        db, actor=admin, action="approve_inspector_request",
        entity_type="inspector_request", entity_id=str(req.id),
        new_value={"status": "approved", "admin_notes": req.admin_notes},
    )

    # Fetch officer name
    officer_res = await db.execute(select(User).where(User.id == req.officer_user_id))
    officer_user = officer_res.scalar_one_or_none()

    if not target_name and req.inspector_data:
        target_name = req.inspector_data.get("full_name")

    return InspectorRequestResponse(
        id=str(req.id),
        request_code=req.request_code,
        request_type=req.request_type.value,
        officer_user_id=str(req.officer_user_id),
        officer_name=officer_user.full_name if officer_user else None,
        target_inspector_id=str(req.target_inspector_id) if req.target_inspector_id else None,
        target_inspector_name=target_name,
        inspector_data=req.inspector_data,
        reason=req.reason,
        status=req.status.value,
        reviewed_by=str(admin.id),
        reviewer_name=admin.full_name,
        admin_notes=req.admin_notes,
        reviewed_at=req.reviewed_at.isoformat(),
        created_at=req.created_at.isoformat(),
        updated_at=req.updated_at.isoformat(),
    )


@router.post("/inspector-requests/{request_id}/reject", response_model=InspectorRequestResponse)
async def reject_inspector_request(
    request_id: str,
    body: InspectorRequestReview,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    """Reject an inspector request (Admin only)."""
    result = await db.execute(select(InspectorRequest).where(InspectorRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Inspector request not found")

    if req.status != InspectorRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request is already {req.status.value}")

    req.status = InspectorRequestStatus.REJECTED
    req.reviewed_by = admin.id
    req.admin_notes = body.admin_notes or "Rejected by Admin"
    req.reviewed_at = datetime.now(timezone.utc)

    await log_audit(
        db, actor=admin, action="reject_inspector_request",
        entity_type="inspector_request", entity_id=str(req.id),
        new_value={"status": "rejected", "admin_notes": req.admin_notes},
    )

    officer_res = await db.execute(select(User).where(User.id == req.officer_user_id))
    officer_user = officer_res.scalar_one_or_none()

    target_name = None
    if req.target_inspector_id:
        t_user = (await db.execute(select(User).where(User.id == req.target_inspector_id))).scalar_one_or_none()
        if t_user:
            target_name = t_user.full_name

    return InspectorRequestResponse(
        id=str(req.id),
        request_code=req.request_code,
        request_type=req.request_type.value,
        officer_user_id=str(req.officer_user_id),
        officer_name=officer_user.full_name if officer_user else None,
        target_inspector_id=str(req.target_inspector_id) if req.target_inspector_id else None,
        target_inspector_name=target_name,
        inspector_data=req.inspector_data,
        reason=req.reason,
        status=req.status.value,
        reviewed_by=str(admin.id),
        reviewer_name=admin.full_name,
        admin_notes=req.admin_notes,
        reviewed_at=req.reviewed_at.isoformat(),
        created_at=req.created_at.isoformat(),
        updated_at=req.updated_at.isoformat(),
    )
