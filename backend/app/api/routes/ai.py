"""AI and risk analysis routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin_or_officer, verify_inspector_project_access
from app.core.database import get_db
from app.models.models import Evidence, EvidenceAnalysis, Project, RiskScore, User
from app.services.ai import analyze_project_evidence, evaluate_project_risk

router = APIRouter(prefix="/api/ai", tags=["ai"])


class TriggerAnalysisRequest(BaseModel):
    evidence_id: str


class RiskScoreResponse(BaseModel):
    id: str
    project_id: str
    overall_score: float
    risk_level: str
    image_risk: float | None = None
    financial_risk: float | None = None
    geospatial_risk: float | None = None
    evidence_risk: float | None = None
    contractor_risk: float | None = None
    explanation: list[str]
    contributing_factors: dict
    is_mock: bool
    calculated_at: str

    model_config = {"from_attributes": True}


class EvidenceAnalysisResponse(BaseModel):
    id: str
    evidence_id: str
    forensics_score: float | None = None
    forensics_indicators: list | None = None
    duplicate_score: float | None = None
    duplicate_matches: list | None = None
    overall_risk: float | None = None
    analysis_metadata: dict | None = None
    is_mock: bool
    processed_at: str

    model_config = {"from_attributes": True}


@router.post("/analyze-evidence")
async def trigger_evidence_analysis(
    body: TriggerAnalysisRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Manually trigger AI analysis for specific evidence (admin/officer)."""
    if current_user.role.value not in ["admin", "district_officer"]:
        raise HTTPException(status_code=403, detail="Requires admin or district officer role")

    ev_result = await db.execute(select(Evidence).where(Evidence.id == body.evidence_id))
    evidence = ev_result.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    proj_result = await db.execute(select(Project).where(Project.id == evidence.project_id))
    project = proj_result.scalar_one()

    analysis = await analyze_project_evidence(evidence, project, db)
    await db.commit()

    return EvidenceAnalysisResponse(
        id=str(analysis.id),
        evidence_id=str(analysis.evidence_id),
        forensics_score=analysis.forensics_score,
        forensics_indicators=analysis.forensics_indicators,
        duplicate_score=analysis.duplicate_score,
        duplicate_matches=analysis.duplicate_matches,
        overall_risk=analysis.overall_risk,
        analysis_metadata=analysis.analysis_metadata,
        is_mock=analysis.is_mock,
        processed_at=analysis.processed_at.isoformat(),
    )


@router.post("/evaluate-risk/{project_id}", response_model=RiskScoreResponse)
async def trigger_risk_evaluation(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin_or_officer)],
):
    """Calculate comprehensive risk score for a project."""
    proj_result = await db.execute(select(Project).where(Project.id == project_id, Project.is_deleted == False))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    risk_score = await evaluate_project_risk(project_id, db)
    await db.commit()

    return RiskScoreResponse(
        id=str(risk_score.id),
        project_id=str(risk_score.project_id),
        overall_score=risk_score.overall_score,
        risk_level=_risk_level(risk_score.overall_score),
        image_risk=risk_score.image_risk,
        financial_risk=risk_score.financial_risk,
        geospatial_risk=risk_score.geospatial_risk,
        evidence_risk=risk_score.evidence_risk,
        contractor_risk=risk_score.contractor_risk,
        explanation=risk_score.explanation or [],
        contributing_factors=risk_score.contributing_factors or {},
        is_mock=risk_score.is_mock,
        calculated_at=risk_score.calculated_at.isoformat(),
    )


@router.get("/risk/{project_id}", response_model=RiskScoreResponse)
async def get_latest_risk_score(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get latest risk score for a project."""
    await verify_inspector_project_access(project_id, current_user, db)

    result = await db.execute(
        select(RiskScore)
        .where(RiskScore.project_id == project_id)
        .order_by(RiskScore.calculated_at.desc())
        .limit(1)
    )
    risk = result.scalar_one_or_none()
    if not risk:
        raise HTTPException(status_code=404, detail="No risk score computed for this project")

    return RiskScoreResponse(
        id=str(risk.id),
        project_id=str(risk.project_id),
        overall_score=risk.overall_score,
        risk_level=_risk_level(risk.overall_score),
        image_risk=risk.image_risk,
        financial_risk=risk.financial_risk,
        geospatial_risk=risk.geospatial_risk,
        evidence_risk=risk.evidence_risk,
        contractor_risk=risk.contractor_risk,
        explanation=risk.explanation or [],
        contributing_factors=risk.contributing_factors or {},
        is_mock=risk.is_mock,
        calculated_at=risk.calculated_at.isoformat(),
    )


@router.get("/evidence-analysis/{evidence_id}", response_model=EvidenceAnalysisResponse)
async def get_evidence_analysis(
    evidence_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get AI analysis for a specific evidence item."""
    result = await db.execute(
        select(EvidenceAnalysis).where(EvidenceAnalysis.evidence_id == evidence_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this evidence")

    # Authorization check
    ev_result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = ev_result.scalar_one()
    await verify_inspector_project_access(str(evidence.project_id), current_user, db)

    return EvidenceAnalysisResponse(
        id=str(analysis.id),
        evidence_id=str(analysis.evidence_id),
        forensics_score=analysis.forensics_score,
        forensics_indicators=analysis.forensics_indicators,
        duplicate_score=analysis.duplicate_score,
        duplicate_matches=analysis.duplicate_matches,
        overall_risk=analysis.overall_risk,
        analysis_metadata=analysis.analysis_metadata,
        is_mock=analysis.is_mock,
        processed_at=analysis.processed_at.isoformat(),
    )


def _risk_level(score: float) -> str:
    if score >= 80:
        return "critical"
    elif score >= 60:
        return "high"
    elif score >= 30:
        return "moderate"
    else:
        return "low"
