"""Expense Bill & Material Price Anomaly routes."""

from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin_or_officer
from app.core.database import get_db
from app.models.enums import AssignmentStatus, ExpenseBillStatus, UserRole
from app.models.models import ExpenseBill, Project, ProjectInspector, User
from app.schemas.bills import (
    BillCreateRequest,
    BillItemInput,
    ExpenseBillResponse,
    MaterialBenchmarkResponse,
)
from app.services.material_prices import (
    analyze_expense_items,
    get_all_benchmarks,
    process_and_save_bill,
)
from app.services.audit import log_audit

router = APIRouter(prefix="/api/bills", tags=["bills"])


async def _build_bill_response(bill: ExpenseBill, db: AsyncSession) -> ExpenseBillResponse:
    """Build full response with project and inspector names."""
    proj_result = await db.execute(select(Project).where(Project.id == bill.project_id))
    project = proj_result.scalar_one_or_none()

    insp_result = await db.execute(select(User).where(User.id == bill.inspector_user_id))
    inspector = insp_result.scalar_one_or_none()

    return ExpenseBillResponse(
        id=str(bill.id),
        bill_code=bill.bill_code,
        project_id=str(bill.project_id),
        project_code=project.project_code if project else None,
        project_name=project.name if project else None,
        inspector_user_id=str(bill.inspector_user_id),
        inspector_name=inspector.full_name if inspector else None,
        vendor_name=bill.vendor_name,
        invoice_number=bill.invoice_number,
        bill_date=bill.bill_date.isoformat(),
        total_amount=float(bill.total_amount),
        file_url=bill.file_url,
        file_name=bill.file_name,
        items=bill.items if isinstance(bill.items, list) else [],
        overall_deviation_pct=bill.overall_deviation_pct,
        anomaly_score=bill.anomaly_score,
        fraud_risk_level=bill.fraud_risk_level,
        ai_analysis_summary=bill.ai_analysis_summary,
        status=bill.status.value,
        created_at=bill.created_at.isoformat(),
        updated_at=bill.updated_at.isoformat(),
    )


@router.get("/benchmarks", response_model=list[MaterialBenchmarkResponse])
async def list_material_benchmarks():
    """Retrieve standard CPWD / State Schedule of Rates benchmarks."""
    benchmarks = get_all_benchmarks()
    return [
        MaterialBenchmarkResponse(
            category=b["category"],
            name=b["name"],
            unit=b["unit"],
            benchmark_price=b["benchmark_price"],
            tolerance_pct=b["tolerance_pct"],
            description=b["description"],
        )
        for b in benchmarks
    ]


@router.post("/analyze-preview")
async def preview_bill_analysis(
    items: list[BillItemInput],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Dry-run AI price anomaly evaluation on line items without persisting to database.
    Useful for interactive frontend live preview.
    """
    raw_items = [item.model_dump() for item in items]
    analysis = analyze_expense_items(raw_items)
    return {
        "items": [item.model_dump() for item in analysis.items],
        "total_amount": analysis.total_amount,
        "overall_deviation_pct": analysis.overall_deviation_pct,
        "anomaly_score": analysis.anomaly_score,
        "fraud_risk_level": analysis.fraud_risk_level,
        "flagged_items_count": analysis.flagged_items_count,
        "ai_summary": analysis.ai_summary,
        "recommended_status": analysis.recommended_status.value,
    }


@router.post("", response_model=ExpenseBillResponse, status_code=status.HTTP_201_CREATED)
async def upload_expense_bill(
    body: BillCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Upload and submit a project expense bill / invoice.
    AI evaluates line items against material benchmarks, flags inflation anomalies,
    updates project expenditure, and generates alerts if fraud risk is detected.
    """
    # Verify project exists
    proj_result = await db.execute(
        select(Project).where(Project.id == body.project_id, Project.is_deleted == False)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Only Field Inspectors are permitted to upload expense bills
    if current_user.role != UserRole.FIELD_INSPECTOR:
        raise HTTPException(
            status_code=403,
            detail="Only Field Inspectors can upload project expense bills for AI auditing.",
        )

    # Ensure field inspector is actively assigned to the project
    assign_result = await db.execute(
        select(ProjectInspector).where(
            ProjectInspector.project_id == body.project_id,
            ProjectInspector.inspector_user_id == current_user.id,
            ProjectInspector.status == AssignmentStatus.ACTIVE,
        )
    )
    if not assign_result.scalar_one_or_none():
        raise HTTPException(
            status_code=403,
            detail="You can only upload expense bills for projects actively assigned to you.",
        )

    raw_items = [item.model_dump() for item in body.items]

    expense_bill = await process_and_save_bill(
        project_id=body.project_id,
        inspector_user=current_user,
        vendor_name=body.vendor_name,
        invoice_number=body.invoice_number,
        bill_date=body.bill_date,
        raw_items=raw_items,
        file_url=body.file_url,
        file_name=body.file_name,
        db=db,
    )

    return await _build_bill_response(expense_bill, db)


@router.get("/project/{project_id}", response_model=list[ExpenseBillResponse])
async def list_project_bills(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """List all expense bills and AI audit reports for a specific project."""
    # Verify project access
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted == False)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role == UserRole.FIELD_INSPECTOR:
        assign_result = await db.execute(
            select(ProjectInspector).where(
                ProjectInspector.project_id == project_id,
                ProjectInspector.inspector_user_id == current_user.id,
                ProjectInspector.status == AssignmentStatus.ACTIVE,
            )
        )
        if not assign_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied to this project's bills")

    result = await db.execute(
        select(ExpenseBill)
        .where(ExpenseBill.project_id == project_id)
        .order_by(ExpenseBill.created_at.desc())
    )
    bills = result.scalars().all()

    return [await _build_bill_response(b, db) for b in bills]


@router.get("/{bill_id}", response_model=ExpenseBillResponse)
async def get_bill_detail(
    bill_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get full forensic breakdown for an individual expense bill."""
    result = await db.execute(select(ExpenseBill).where(ExpenseBill.id == bill_id))
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Expense bill not found")

    return await _build_bill_response(bill, db)


class BillStatusUpdateRequest(BaseModel):
    status: ExpenseBillStatus
    review_notes: str | None = None


@router.patch("/{bill_id}/status", response_model=ExpenseBillResponse)
async def update_bill_status(
    bill_id: str,
    body: BillStatusUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin_or_officer)],
):
    """Approve, reject, or flag an expense bill after officer/auditor review."""
    result = await db.execute(select(ExpenseBill).where(ExpenseBill.id == bill_id))
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Expense bill not found")

    prev_status = bill.status.value
    bill.status = body.status

    await log_audit(
        db,
        actor=current_user,
        action="update_bill_status",
        entity_type="expense_bill",
        entity_id=str(bill.id),
        previous_value={"status": prev_status},
        new_value={"status": body.status.value, "notes": body.review_notes},
    )

    await db.commit()
    await db.refresh(bill)

    return await _build_bill_response(bill, db)
