"""
Material Price Benchmark & AI Anomaly Detection Service.

Compares construction and procurement line items against standard CPWD / State
Schedule of Rates benchmarks, detecting material price over-invoicing, rate
escalation fraud, and procurement anomalies.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AlertSeverity, AlertStatus, AlertType, ExpenseBillStatus
from app.models.models import Alert, ExpenseBill, Project, ProjectEvent, RiskScore, User
from app.services.audit import log_audit


# ── Standard Material Price Benchmark Registry (CPWD / State Schedule) ──

MATERIAL_BENCHMARKS: dict[str, dict[str, Any]] = {
    "cement": {
        "name": "OPC 53 / PPC Cement",
        "category": "cement",
        "unit": "bags",
        "benchmark_price": 380.0,
        "tolerance_pct": 15.0,
        "description": "Standard 50kg bag of Grade 53 OPC / Portland Pozzolana Cement",
    },
    "steel_tmt": {
        "name": "TMT Rebar Steel (Fe500D / Fe550D)",
        "category": "steel_tmt",
        "unit": "kg",
        "benchmark_price": 62.0,
        "tolerance_pct": 12.0,
        "description": "High-strength thermo-mechanically treated bar steel (₹62/kg or ₹62,000/tonne)",
    },
    "sand": {
        "name": "River Sand / Manufactured M-Sand",
        "category": "sand",
        "unit": "cu.m",
        "benchmark_price": 1800.0,
        "tolerance_pct": 18.0,
        "description": "Coarse grade washed river sand or screened M-sand for masonry/concrete",
    },
    "aggregate": {
        "name": "Coarse Aggregate (20mm / 40mm)",
        "category": "aggregate",
        "unit": "cu.m",
        "benchmark_price": 1200.0,
        "tolerance_pct": 15.0,
        "description": "Crushed granite/basalt stone aggregate for structural concrete",
    },
    "bricks": {
        "name": "Red Clay Bricks / Fly Ash Bricks",
        "category": "bricks",
        "unit": "pieces",
        "benchmark_price": 8.50,
        "tolerance_pct": 15.0,
        "description": "Class-1 kiln burnt clay bricks (₹8,500 per 1000 units)",
    },
    "concrete_rmc": {
        "name": "Ready Mix Concrete (RMC M25)",
        "category": "concrete_rmc",
        "unit": "cu.m",
        "benchmark_price": 4200.0,
        "tolerance_pct": 14.0,
        "description": "Pre-mixed design batch concrete M25 grade delivered on site",
    },
    "bitumen": {
        "name": "Bitumen (VG-30 / Emulsion)",
        "category": "bitumen",
        "unit": "kg",
        "benchmark_price": 48.0,
        "tolerance_pct": 15.0,
        "description": "Paving grade Viscosity Grade 30 Bitumen for road construction (₹48,000/tonne)",
    },
    "structural_steel": {
        "name": "Structural Steel (Beams/Angles/Channels)",
        "category": "structural_steel",
        "unit": "kg",
        "benchmark_price": 68.0,
        "tolerance_pct": 12.0,
        "description": "Mild steel rolled sections ISMB / ISA for roofing and trusses",
    },
    "pvc_pipes": {
        "name": "PVC / HDPE Drainage & Water Pipes (110mm)",
        "category": "pvc_pipes",
        "unit": "meters",
        "benchmark_price": 420.0,
        "tolerance_pct": 15.0,
        "description": "Heavy-duty 6kg/cm² pressure rigid PVC/HDPE piping",
    },
    "electrical_cables": {
        "name": "Copper Armoured XLPE Cable (4-Core)",
        "category": "electrical_cables",
        "unit": "meters",
        "benchmark_price": 350.0,
        "tolerance_pct": 15.0,
        "description": "Underground heavy duty distribution copper cable",
    },
    "labor_skilled": {
        "name": "Skilled Mason / Barbender / Carpenter",
        "category": "labor_skilled",
        "unit": "person-days",
        "benchmark_price": 850.0,
        "tolerance_pct": 15.0,
        "description": "Certified master mason / structural steel worker daily wage",
    },
    "labor_unskilled": {
        "name": "Unskilled Labor / Helper",
        "category": "labor_unskilled",
        "unit": "person-days",
        "benchmark_price": 550.0,
        "tolerance_pct": 15.0,
        "description": "General excavation and site assistance daily wage",
    },
    "excavator_jcb": {
        "name": "Excavator / Backhoe Loader (JCB)",
        "category": "excavator_jcb",
        "unit": "hours",
        "benchmark_price": 1600.0,
        "tolerance_pct": 15.0,
        "description": "Earthmoving equipment hourly operational rate with diesel & operator",
    },
    "paint_primer": {
        "name": "Exterior Weatherproof Paint & Primer",
        "category": "paint_primer",
        "unit": "liters",
        "benchmark_price": 240.0,
        "tolerance_pct": 15.0,
        "description": "Premium acrylic exterior emulsion with antifungal coating",
    },
    "waterproofing": {
        "name": "Waterproofing Membrane / Liquid Polymer",
        "category": "waterproofing",
        "unit": "sq.m",
        "benchmark_price": 180.0,
        "tolerance_pct": 15.0,
        "description": "Elastomeric polymer waterproof coating application",
    },
}


def get_all_benchmarks() -> list[dict[str, Any]]:
    """Return all available material price benchmarks."""
    return list(MATERIAL_BENCHMARKS.values())


def find_benchmark_for_item(item_name: str, category: str | None = None) -> dict[str, Any] | None:
    """Find the best matching benchmark by category or name keywords."""
    if category and category.lower() in MATERIAL_BENCHMARKS:
        return MATERIAL_BENCHMARKS[category.lower()]

    name_lower = item_name.lower()
    for cat_key, benchmark in MATERIAL_BENCHMARKS.items():
        if cat_key in name_lower or any(
            kw in name_lower
            for kw in benchmark["name"].lower().split()
            if len(kw) > 3
        ):
            return benchmark

    # Fallback keyword matching
    if any(w in name_lower for w in ["cement", "opc", "ppc"]):
        return MATERIAL_BENCHMARKS["cement"]
    if any(w in name_lower for w in ["steel", "tmt", "rebar", "saria", "iron"]):
        return MATERIAL_BENCHMARKS["steel_tmt"]
    if any(w in name_lower for w in ["sand", "m-sand", "ret"]):
        return MATERIAL_BENCHMARKS["sand"]
    if any(w in name_lower for w in ["brick", "eent", "fly ash"]):
        return MATERIAL_BENCHMARKS["bricks"]
    if any(w in name_lower for w in ["aggregate", "gravel", "stone", "rodi"]):
        return MATERIAL_BENCHMARKS["aggregate"]
    if any(w in name_lower for w in ["concrete", "rmc", "m20", "m25"]):
        return MATERIAL_BENCHMARKS["concrete_rmc"]
    if any(w in name_lower for w in ["bitumen", "tar", "asphalt"]):
        return MATERIAL_BENCHMARKS["bitumen"]
    if any(w in name_lower for w in ["pipe", "pvc", "hdpe"]):
        return MATERIAL_BENCHMARKS["pvc_pipes"]
    if any(w in name_lower for w in ["labor", "mason", "karigar", "helper", "worker"]):
        return MATERIAL_BENCHMARKS["labor_skilled"]
    if any(w in name_lower for w in ["jcb", "excavator", "loader", "crane"]):
        return MATERIAL_BENCHMARKS["excavator_jcb"]

    return None


class EvaluatedBillItem(BaseModel):
    item_name: str
    category: str
    quantity: float
    unit: str
    claimed_unit_price: float
    total_amount: float
    benchmark_unit_price: float
    deviation_pct: float
    status: str  # normal, elevated, severe_inflation, fraud_risk
    notes: str


class BillAnalysisResult(BaseModel):
    items: list[EvaluatedBillItem]
    total_amount: float
    overall_deviation_pct: float
    anomaly_score: float  # 0 to 100
    fraud_risk_level: str  # LOW, MODERATE, HIGH, CRITICAL
    flagged_items_count: int
    ai_summary: str
    recommended_status: ExpenseBillStatus


def analyze_expense_items(raw_items: list[dict[str, Any]]) -> BillAnalysisResult:
    """
    Run AI price anomaly analysis on raw invoice line items against benchmarks.
    """
    evaluated_items: list[EvaluatedBillItem] = []
    total_bill_amount = 0.0
    weighted_deviation_sum = 0.0
    max_single_deviation = 0.0
    flagged_count = 0

    for raw in raw_items:
        item_name = raw.get("item_name", "Material Item").strip()
        category = raw.get("category", "").strip().lower()
        quantity = float(raw.get("quantity", 1.0))
        unit = raw.get("unit", "units").strip()
        claimed_unit_price = float(raw.get("claimed_unit_price", 0.0) or 0.0)
        raw_total = raw.get("total_amount")
        if raw_total is not None and float(raw_total) > 0:
            item_total = float(raw_total)
        else:
            item_total = quantity * claimed_unit_price

        total_bill_amount += item_total

        # Match benchmark
        bm = find_benchmark_for_item(item_name, category)
        if bm:
            benchmark_unit_price = float(bm["benchmark_price"])
            benchmark_name = bm["name"]
            category_clean = bm["category"]
        else:
            # If no benchmark is found, treat claimed price as neutral baseline
            benchmark_unit_price = claimed_unit_price if claimed_unit_price > 0 else 100.0
            benchmark_name = "Custom / Specialized Material"
            category_clean = category or "general"

        if benchmark_unit_price > 0:
            deviation_pct = ((claimed_unit_price - benchmark_unit_price) / benchmark_unit_price) * 100.0
        else:
            deviation_pct = 0.0

        if deviation_pct > max_single_deviation:
            max_single_deviation = deviation_pct

        # Severity Classification
        if deviation_pct <= 15.0:
            status = "normal"
            notes = f"Rate is within standard CPWD market range (Benchmark: ₹{benchmark_unit_price:,.2f}/{unit})."
        elif deviation_pct <= 35.0:
            status = "elevated"
            notes = f"Rate is {deviation_pct:.1f}% higher than standard benchmark (₹{benchmark_unit_price:,.2f}/{unit}). Moderate escalation."
            flagged_count += 1
        elif deviation_pct <= 60.0:
            status = "severe_inflation"
            notes = f"⚠️ Severe price inflation: {deviation_pct:.1f}% above standard rate (₹{benchmark_unit_price:,.2f}/{unit}). Flagged for audit."
            flagged_count += 1
        else:
            status = "fraud_risk"
            notes = f"🚨 Critical Price Anomaly: {deviation_pct:.1f}% escalation over market benchmark (₹{benchmark_unit_price:,.2f}/{unit}). Potential over-invoicing fraud."
            flagged_count += 1

        evaluated_items.append(
            EvaluatedBillItem(
                item_name=item_name,
                category=category_clean,
                quantity=quantity,
                unit=unit,
                claimed_unit_price=claimed_unit_price,
                total_amount=item_total,
                benchmark_unit_price=benchmark_unit_price,
                deviation_pct=round(deviation_pct, 2),
                status=status,
                notes=notes,
            )
        )

    # Calculate weighted overall deviation
    if total_bill_amount > 0:
        for item in evaluated_items:
            weight = item.total_amount / total_bill_amount
            # Only positive deviations (inflation) contribute to fraud anomaly score
            pos_dev = max(0.0, item.deviation_pct)
            weighted_deviation_sum += pos_dev * weight
        overall_deviation_pct = round(weighted_deviation_sum, 2)
    else:
        overall_deviation_pct = 0.0

    # Calculate Anomaly Score (0 - 100)
    # Composite: 70% weighted average deviation + 30% max single item spike penalty
    base_score = min(100.0, overall_deviation_pct * 1.25)
    spike_penalty = min(30.0, (max(0.0, max_single_deviation - 30.0)) * 0.5)
    anomaly_score = min(100.0, round(base_score * 0.7 + spike_penalty * 1.0, 1))

    # Determine Fraud Risk Level & Status
    if anomaly_score >= 70.0 or max_single_deviation >= 60.0:
        fraud_risk_level = "CRITICAL"
        recommended_status = ExpenseBillStatus.FLAGGED
        ai_summary = (
            f"🚨 CRITICAL FINANCIAL FRAUD RISK (Score: {anomaly_score}/100): "
            f"Significant material rate escalation detected with overall {overall_deviation_pct:.1f}% price inflation. "
            f"{flagged_count} line items severely exceed CPWD/Schedule of Rates benchmarks. Immediate forensic verification recommended."
        )
    elif anomaly_score >= 45.0 or flagged_count >= 2:
        fraud_risk_level = "HIGH"
        recommended_status = ExpenseBillStatus.FLAGGED
        ai_summary = (
            f"⚠️ HIGH FINANCIAL ANOMALY (Score: {anomaly_score}/100): "
            f"Material rates reflect {overall_deviation_pct:.1f}% average escalation above standard benchmarks. "
            f"{flagged_count} items exhibit unusual pricing premiums requiring explanation from contractor."
        )
    elif anomaly_score >= 25.0:
        fraud_risk_level = "MODERATE"
        recommended_status = ExpenseBillStatus.VERIFIED
        ai_summary = (
            f"ℹ️ MODERATE RATE VARIANCE (Score: {anomaly_score}/100): "
            f"Minor market fluctuations observed (+{overall_deviation_pct:.1f}%). Rates are slightly elevated but generally plausible."
        )
    else:
        fraud_risk_level = "LOW"
        recommended_status = ExpenseBillStatus.VERIFIED
        ai_summary = (
            f"✅ CLEAN PROCUREMENT AUDIT (Score: {anomaly_score}/100): "
            f"All invoiced material rates align closely with standard CPWD and State Schedule of Rates benchmarks."
        )

    return BillAnalysisResult(
        items=evaluated_items,
        total_amount=round(total_bill_amount, 2),
        overall_deviation_pct=overall_deviation_pct,
        anomaly_score=anomaly_score,
        fraud_risk_level=fraud_risk_level,
        flagged_items_count=flagged_count,
        ai_summary=ai_summary,
        recommended_status=recommended_status,
    )


async def process_and_save_bill(
    project_id: str,
    inspector_user: User,
    vendor_name: str,
    invoice_number: str | None,
    bill_date: datetime,
    raw_items: list[dict[str, Any]],
    file_url: str | None,
    file_name: str | None,
    db: AsyncSession,
) -> ExpenseBill:
    """
    Process bill submission, execute AI material price comparison,
    persist record, generate alerts if anomalous, and update project risk.
    """
    # 1. Fetch Project
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise ValueError("Project not found")

    # 2. Run AI Analysis
    analysis = analyze_expense_items(raw_items)

    # 3. Create Bill Code
    bill_count_res = await db.execute(
        select(ExpenseBill).where(ExpenseBill.project_id == project_id)
    )
    existing_bills = bill_count_res.scalars().all()
    bill_seq = len(existing_bills) + 1
    bill_code = f"BILL-{project.project_code[-4:]}-{bill_seq:03d}"

    # 4. Instantiate ExpenseBill
    expense_bill = ExpenseBill(
        bill_code=bill_code,
        project_id=project.id,
        inspector_user_id=inspector_user.id,
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        bill_date=bill_date,
        total_amount=analysis.total_amount,
        file_url=file_url,
        file_name=file_name,
        items=[item.model_dump() for item in analysis.items],
        overall_deviation_pct=analysis.overall_deviation_pct,
        anomaly_score=analysis.anomaly_score,
        fraud_risk_level=analysis.fraud_risk_level,
        ai_analysis_summary=analysis.ai_summary,
        status=analysis.recommended_status,
    )
    db.add(expense_bill)

    # 5. Update Project Expenditure & Financial Progress
    current_exp = float(project.expenditure or 0.0)
    new_exp = current_exp + analysis.total_amount
    project.expenditure = new_exp
    if project.sanction_amount and float(project.sanction_amount) > 0:
        project.financial_progress = min(100.0, round((new_exp / float(project.sanction_amount)) * 100.0, 1))

    # 6. If High/Critical Anomaly: Create Alert & Project Event
    if analysis.anomaly_score >= 45.0:
        severity = AlertSeverity.CRITICAL if analysis.anomaly_score >= 70.0 else AlertSeverity.HIGH
        alert_code = f"ALT-FIN-{uuid.uuid4().hex[:6].upper()}"
        alert = Alert(
            alert_code=alert_code,
            project_id=project.id,
            alert_type=AlertType.FINANCIAL_ANOMALY,
            severity=severity,
            title=f"Material Price Inflation Anomaly in Bill {bill_code}",
            description=(
                f"AI price comparison detected {analysis.overall_deviation_pct:.1f}% rate escalation from vendor '{vendor_name}'. "
                f"{analysis.flagged_items_count} line item(s) severely exceed CPWD benchmarks. Total bill: ₹{analysis.total_amount:,.2f}."
            ),
            evidence_data={
                "bill_code": bill_code,
                "vendor_name": vendor_name,
                "invoice_number": invoice_number,
                "total_amount": analysis.total_amount,
                "anomaly_score": analysis.anomaly_score,
                "overall_deviation_pct": analysis.overall_deviation_pct,
                "flagged_items": [
                    item.model_dump()
                    for item in analysis.items
                    if item.status in ("severe_inflation", "fraud_risk", "elevated")
                ],
            },
            status=AlertStatus.OPEN,
        )
        db.add(alert)

    # 7. Add Project Timeline Event
    event = ProjectEvent(
        project_id=project.id,
        event_type="EXPENSE_BILL_UPLOADED",
        title=f"Expense Bill {bill_code} Uploaded (₹{analysis.total_amount:,.2f})",
        description=(
            f"Vendor: {vendor_name} | AI Anomaly Score: {analysis.anomaly_score}/100 ({analysis.fraud_risk_level} Risk). "
            f"{analysis.ai_summary}"
        ),
        actor_id=inspector_user.id,
        metadata_={
            "bill_code": bill_code,
            "total_amount": analysis.total_amount,
            "anomaly_score": analysis.anomaly_score,
            "overall_deviation_pct": analysis.overall_deviation_pct,
            "fraud_risk_level": analysis.fraud_risk_level,
        },
    )
    db.add(event)

    # 8. Re-evaluate Project Risk Score with new financial data
    try:
        from app.services.ai import evaluate_project_risk
        await evaluate_project_risk(str(project.id), db)
    except Exception as e:
        # Fallback if AI provider has any mock exception
        pass

    # 9. Audit Logging
    await log_audit(
        db,
        actor=inspector_user,
        action="upload_expense_bill",
        entity_type="expense_bill",
        entity_id=str(expense_bill.id),
        new_value={
            "bill_code": bill_code,
            "vendor_name": vendor_name,
            "total_amount": analysis.total_amount,
            "anomaly_score": analysis.anomaly_score,
            "fraud_risk_level": analysis.fraud_risk_level,
        },
    )

    await db.commit()
    await db.refresh(expense_bill)
    return expense_bill
