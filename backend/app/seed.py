"""
Seed script: creates demo users, contractors, projects, inspections,
evidence analysis results, risk scores, and alerts.

Run: python -m app.seed
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, engine, Base
from app.core.security import hash_password
from app.models.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    AssignmentStatus,
    EvidenceStatus,
    ExpenseBillStatus,
    InspectionStatus,
    ProjectStatus,
    ProjectType,
    UserRole,
)
from app.models.models import (
    Alert,
    Contractor,
    Evidence,
    EvidenceAnalysis,
    ExpenseBill,
    FinancialRecord,
    Inspection,
    Project,
    ProjectEvent,
    ProjectInspector,
    RiskScore,
    User,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _now() - timedelta(days=n)


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Check if already seeded
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        # ── Users ───────────────────────────────────────────────────

        admin = User(
            email="admin@satark.gov.in",
            hashed_password=hash_password("admin123"),
            full_name="Dr. Rajesh Kumar",
            role=UserRole.ADMIN,
            state="Karnataka",
            district="Bengaluru Urban",
        )

        inspector1 = User(
            email="inspector1@satark.gov.in",
            hashed_password=hash_password("inspector123"),
            full_name="Priya Sharma",
            role=UserRole.FIELD_INSPECTOR,
            inspector_id="INS-0042",
            phone="+91-9876543210",
            state="Karnataka",
            district="Bengaluru Urban",
        )

        inspector2 = User(
            email="inspector2@satark.gov.in",
            hashed_password=hash_password("inspector123"),
            full_name="Amit Patel",
            role=UserRole.FIELD_INSPECTOR,
            inspector_id="INS-0078",
            phone="+91-9876543211",
            state="Karnataka",
            district="Mysuru",
        )

        inspector3 = User(
            email="inspector3@satark.gov.in",
            hashed_password=hash_password("inspector123"),
            full_name="Kavitha Reddy",
            role=UserRole.FIELD_INSPECTOR,
            inspector_id="INS-0105",
            phone="+91-9876543212",
            state="Telangana",
            district="Hyderabad",
        )

        officer = User(
            email="officer@satark.gov.in",
            hashed_password=hash_password("officer123"),
            full_name="Sanjay Mehra (IAS)",
            role=UserRole.DISTRICT_OFFICER,
            state="Karnataka",
            district="Bengaluru Urban",
        )

        auditor = User(
            email="auditor@satark.gov.in",
            hashed_password=hash_password("auditor123"),
            full_name="Meena Iyer",
            role=UserRole.AUDITOR,
            state="Karnataka",
        )

        db.add_all([admin, inspector1, inspector2, inspector3, officer, auditor])
        await db.flush()

        # ── Contractors ─────────────────────────────────────────────

        contractor1 = Contractor(
            name="Sri Lakshmi Constructions",
            registration_number="KA-CON-2024-0142",
            contact_person="B. Ramesh",
            phone="+91-8012345678",
            state="Karnataka",
            district="Bengaluru Urban",
        )
        contractor2 = Contractor(
            name="Bharat Infrastructure Pvt. Ltd.",
            registration_number="KA-CON-2023-0087",
            contact_person="Suresh Gowda",
            phone="+91-8012345679",
            state="Karnataka",
            district="Mysuru",
        )
        contractor3 = Contractor(
            name="National Builders Co.",
            registration_number="TS-CON-2024-0231",
            contact_person="K. Venkat Rao",
            phone="+91-9100034567",
            state="Telangana",
            district="Hyderabad",
        )
        db.add_all([contractor1, contractor2, contractor3])
        await db.flush()

        # ── Projects ────────────────────────────────────────────────

        # Project A: SUSPICIOUS — financial/physical mismatch
        proj_a = Project(
            project_code="MPLADS-KA-2025-0147",
            name="Community Health Center Construction — Yelahanka",
            description="Construction of a 30-bed community health center with OPD, pharmacy, and diagnostic lab.",
            project_type=ProjectType.HOSPITAL,
            state="Karnataka",
            district="Bengaluru Urban",
            constituency="Bengaluru North",
            village_locality="Yelahanka New Town",
            latitude=13.1007,
            longitude=77.5963,
            inspection_radius_m=150,
            sanction_amount=4500000,
            released_amount=4200000,
            expenditure=4095000,
            physical_progress=42,
            financial_progress=91,
            contractor_id=contractor1.id,
            start_date=_days_ago(180),
            expected_completion_date=_days_ago(-60),
            status=ProjectStatus.HIGH_RISK,
            created_by=admin.id,
        )

        # Project B: SUSPICIOUS — duplicate evidence
        proj_b = Project(
            project_code="MPLADS-KA-2025-0203",
            name="Village Road Widening — Kengeri to Kumbalagodu",
            description="Widening of 2.5 km village road from single lane to double lane with drainage.",
            project_type=ProjectType.ROAD,
            state="Karnataka",
            district="Bengaluru Urban",
            constituency="Rajarajeshwarinagar",
            village_locality="Kumbalagodu",
            latitude=12.8985,
            longitude=77.4879,
            inspection_radius_m=200,
            sanction_amount=3200000,
            released_amount=2800000,
            expenditure=2650000,
            physical_progress=65,
            financial_progress=83,
            contractor_id=contractor1.id,
            start_date=_days_ago(120),
            expected_completion_date=_days_ago(-30),
            status=ProjectStatus.UNDER_REVIEW,
            created_by=admin.id,
        )

        # Project C: SUSPICIOUS — geofence violation
        proj_c = Project(
            project_code="MPLADS-KA-2025-0089",
            name="Primary School Renovation — Hebbal Ward",
            description="Renovation of government primary school including roof repair, painting, new furniture.",
            project_type=ProjectType.SCHOOL,
            state="Karnataka",
            district="Bengaluru Urban",
            constituency="Bengaluru North",
            village_locality="Hebbal",
            latitude=13.0358,
            longitude=77.5970,
            inspection_radius_m=100,
            sanction_amount=1800000,
            released_amount=1500000,
            expenditure=1380000,
            physical_progress=70,
            financial_progress=77,
            contractor_id=contractor2.id,
            start_date=_days_ago(90),
            expected_completion_date=_days_ago(-15),
            status=ProjectStatus.ESCALATED,
            created_by=admin.id,
        )

        # Project D: CLEAN — low risk
        proj_d = Project(
            project_code="MPLADS-KA-2025-0312",
            name="Drinking Water Pipeline — Whitefield",
            description="Installation of 3 km drinking water pipeline from overhead tank to distribution network.",
            project_type=ProjectType.DRINKING_WATER,
            state="Karnataka",
            district="Bengaluru Urban",
            constituency="Mahadevapura",
            village_locality="Whitefield",
            latitude=12.9698,
            longitude=77.7500,
            inspection_radius_m=250,
            sanction_amount=2500000,
            released_amount=2000000,
            expenditure=1800000,
            physical_progress=72,
            financial_progress=72,
            contractor_id=contractor2.id,
            start_date=_days_ago(150),
            expected_completion_date=_days_ago(-45),
            status=ProjectStatus.UNDER_INSPECTION,
            created_by=admin.id,
        )

        # Project E: Mysuru district — assigned to inspector2
        proj_e = Project(
            project_code="MPLADS-KA-2025-0456",
            name="Community Hall Construction — Mysuru South",
            description="Construction of multi-purpose community hall with capacity of 200 persons.",
            project_type=ProjectType.COMMUNITY_HALL,
            state="Karnataka",
            district="Mysuru",
            constituency="Krishnaraja",
            village_locality="Jayalakshmipuram",
            latitude=12.3051,
            longitude=76.6551,
            inspection_radius_m=120,
            sanction_amount=5000000,
            released_amount=3500000,
            expenditure=3200000,
            physical_progress=60,
            financial_progress=64,
            contractor_id=contractor2.id,
            start_date=_days_ago(200),
            expected_completion_date=_days_ago(-20),
            status=ProjectStatus.INSPECTOR_ASSIGNED,
            created_by=admin.id,
        )

        # Project F: Hyderabad — assigned to inspector3
        proj_f = Project(
            project_code="MPLADS-TS-2025-0078",
            name="Street Electrification — Kukatpally",
            description="Installation of 80 LED street lights along main roads and colony internal roads.",
            project_type=ProjectType.ELECTRIFICATION,
            state="Telangana",
            district="Hyderabad",
            constituency="Kukatpally",
            village_locality="KPHB Colony",
            latitude=17.4947,
            longitude=78.3996,
            inspection_radius_m=300,
            sanction_amount=1200000,
            released_amount=1000000,
            expenditure=920000,
            physical_progress=85,
            financial_progress=77,
            contractor_id=contractor3.id,
            start_date=_days_ago(100),
            expected_completion_date=_days_ago(-10),
            status=ProjectStatus.COMPLETED,
            created_by=admin.id,
        )

        db.add_all([proj_a, proj_b, proj_c, proj_d, proj_e, proj_f])
        await db.flush()

        # ── Assignments ─────────────────────────────────────────────

        assignments = [
            ProjectInspector(project_id=proj_a.id, inspector_user_id=inspector1.id, assigned_by=admin.id),
            ProjectInspector(project_id=proj_b.id, inspector_user_id=inspector1.id, assigned_by=admin.id),
            ProjectInspector(project_id=proj_c.id, inspector_user_id=inspector1.id, assigned_by=admin.id),
            ProjectInspector(project_id=proj_d.id, inspector_user_id=inspector1.id, assigned_by=admin.id),
            ProjectInspector(project_id=proj_e.id, inspector_user_id=inspector2.id, assigned_by=admin.id),
            ProjectInspector(project_id=proj_f.id, inspector_user_id=inspector3.id, assigned_by=admin.id),
        ]
        db.add_all(assignments)
        await db.flush()

        # ── Risk Scores ─────────────────────────────────────────────

        risk_a = RiskScore(
            project_id=proj_a.id,
            overall_score=87,
            image_risk=91,
            financial_risk=92,
            geospatial_risk=45,
            evidence_risk=78,
            contractor_risk=65,
            is_mock=True,
            explanation=[
                "Physical progress (42%) significantly lower than financial expenditure (91%)",
                "3 evidence images show high similarity to historical submissions",
                "Material cost exceeds district benchmark by 28%",
                "Contractor has 2 other high-risk projects in same district",
            ],
            contributing_factors={
                "progress_expenditure_gap": 49,
                "duplicate_evidence_count": 3,
                "cost_variance_pct": 28,
                "contractor_risk_flag": True,
            },
        )

        risk_b = RiskScore(
            project_id=proj_b.id,
            overall_score=82,
            image_risk=88,
            financial_risk=61,
            geospatial_risk=72,
            evidence_risk=85,
            contractor_risk=65,
            is_mock=True,
            explanation=[
                "94% image similarity detected with evidence from Project MPLADS-KA-2025-0147",
                "Potential evidence reuse detected — requires review",
                "Financial progress 18% ahead of physical progress",
                "Same contractor as high-risk Project A",
            ],
            contributing_factors={
                "max_similarity_score": 94,
                "duplicate_project_code": "MPLADS-KA-2025-0147",
                "progress_gap": 18,
            },
        )

        risk_c = RiskScore(
            project_id=proj_c.id,
            overall_score=76,
            image_risk=55,
            financial_risk=40,
            geospatial_risk=95,
            evidence_risk=82,
            contractor_risk=30,
            is_mock=True,
            explanation=[
                "Evidence captured 2.3 km from project site (geofence: 100m)",
                "GPS accuracy very low (45m) during 2 of 5 evidence captures",
                "Location evidence does not match the configured project geofence",
            ],
            contributing_factors={
                "max_geofence_violation_m": 2300,
                "low_gps_captures": 2,
            },
        )

        risk_d = RiskScore(
            project_id=proj_d.id,
            overall_score=18,
            image_risk=12,
            financial_risk=15,
            geospatial_risk=8,
            evidence_risk=10,
            contractor_risk=20,
            is_mock=True,
            explanation=[
                "All evidence within project geofence",
                "Financial and physical progress aligned",
                "No duplicate evidence detected",
            ],
            contributing_factors={},
        )

        risk_e = RiskScore(
            project_id=proj_e.id,
            overall_score=35,
            image_risk=30,
            financial_risk=25,
            geospatial_risk=20,
            evidence_risk=40,
            contractor_risk=35,
            is_mock=True,
            explanation=[
                "Minor financial progress gap (4%)",
                "Evidence metadata partially unavailable for 1 image",
            ],
            contributing_factors={},
        )

        risk_f = RiskScore(
            project_id=proj_f.id,
            overall_score=12,
            image_risk=10,
            financial_risk=8,
            geospatial_risk=5,
            evidence_risk=15,
            contractor_risk=10,
            is_mock=True,
            explanation=[
                "Project completed successfully",
                "All verifications passed",
            ],
            contributing_factors={},
        )

        db.add_all([risk_a, risk_b, risk_c, risk_d, risk_e, risk_f])
        await db.flush()

        # ── Alerts ──────────────────────────────────────────────────

        alerts = [
            Alert(
                alert_code="ALT-0001",
                project_id=proj_a.id,
                alert_type=AlertType.PROGRESS_MISMATCH,
                severity=AlertSeverity.CRITICAL,
                title="Severe progress–expenditure decoupling detected",
                description="Physical progress 42% against 91% financial expenditure. Gap of 49 percentage points exceeds threshold.",
                evidence_data={"physical": 42, "financial": 91, "gap": 49},
            ),
            Alert(
                alert_code="ALT-0002",
                project_id=proj_a.id,
                alert_type=AlertType.FINANCIAL_ANOMALY,
                severity=AlertSeverity.HIGH,
                title="Material cost exceeds district benchmark",
                description="Reported material cost exceeds benchmark for similar projects in Bengaluru Urban by 28%.",
                evidence_data={"variance_pct": 28},
            ),
            Alert(
                alert_code="ALT-0003",
                project_id=proj_b.id,
                alert_type=AlertType.DUPLICATE_EVIDENCE,
                severity=AlertSeverity.CRITICAL,
                title="Potential evidence reuse detected",
                description="Evidence image shows 94% similarity with evidence from Project MPLADS-KA-2025-0147 submitted 4 months ago.",
                evidence_data={"similarity": 94, "matched_project": "MPLADS-KA-2025-0147"},
            ),
            Alert(
                alert_code="ALT-0004",
                project_id=proj_c.id,
                alert_type=AlertType.GEOFENCE_VIOLATION,
                severity=AlertSeverity.HIGH,
                title="Evidence captured outside project geofence",
                description="Evidence captured 2.3 km from project site. Project geofence radius is 100 meters.",
                evidence_data={"distance_m": 2300, "radius_m": 100},
            ),
            Alert(
                alert_code="ALT-0005",
                project_id=proj_c.id,
                alert_type=AlertType.GPS_ACCURACY_LOW,
                severity=AlertSeverity.MEDIUM,
                title="GPS accuracy insufficient for verification",
                description="GPS accuracy of 45m recorded during evidence capture. Minimum recommended accuracy: 20m.",
                evidence_data={"accuracy_m": 45, "threshold_m": 20},
            ),
            Alert(
                alert_code="ALT-0006",
                project_id=proj_a.id,
                alert_type=AlertType.CONTRACTOR_ANOMALY,
                severity=AlertSeverity.HIGH,
                title="Contractor concentration anomaly",
                description="Sri Lakshmi Constructions has 2 high-risk projects in Bengaluru Urban district within the same period.",
                evidence_data={"contractor": "Sri Lakshmi Constructions", "high_risk_count": 2},
            ),
        ]
        db.add_all(alerts)

        # ── Project Events (Timeline) ──────────────────────────────

        for proj in [proj_a, proj_b, proj_c, proj_d, proj_e, proj_f]:
            db.add(ProjectEvent(
                project_id=proj.id,
                event_type="project_created",
                title="Project Created",
                description=f"Project {proj.project_code} created",
                actor_id=admin.id,
                created_at=proj.start_date or _days_ago(180),
            ))
            db.add(ProjectEvent(
                project_id=proj.id,
                event_type="inspector_assigned",
                title="Inspector Assigned",
                description="Field inspector assigned for verification",
                actor_id=admin.id,
                created_at=(proj.start_date or _days_ago(180)) + timedelta(days=7),
            ))

        # Extra events for suspicious projects
        db.add(ProjectEvent(
            project_id=proj_a.id,
            event_type="risk_score_updated",
            title="Risk Score Updated to 87/100 (Critical)",
            description="Multiple anomaly signals detected by risk engine",
            created_at=_days_ago(5),
        ))
        db.add(ProjectEvent(
            project_id=proj_a.id,
            event_type="alert_created",
            title="Critical Alert: Progress–Expenditure Mismatch",
            description="Financial expenditure (91%) far exceeds physical progress (42%)",
            created_at=_days_ago(5),
        ))
        db.add(ProjectEvent(
            project_id=proj_b.id,
            event_type="alert_created",
            title="Critical Alert: Potential Evidence Reuse",
            description="94% image similarity detected with another project",
            created_at=_days_ago(3),
        ))

        # ── Expense Bills & Invoices ─────────────────────────────────
        bill_clean = ExpenseBill(
            bill_code="BILL-0456-001",
            project_id=proj_e.id,
            inspector_user_id=inspector2.id,
            vendor_name="Karnataka State Granites & Aggregates Ltd",
            invoice_number="INV-2025-1102",
            bill_date=_days_ago(30),
            total_amount=328000.0,
            items=[
                {
                    "item_name": "OPC 53 Grade Cement",
                    "category": "cement",
                    "quantity": 400,
                    "unit": "bags",
                    "claimed_unit_price": 385.0,
                    "total_amount": 154000.0,
                    "benchmark_unit_price": 380.0,
                    "deviation_pct": 1.32,
                    "status": "normal",
                    "notes": "Rate is within standard CPWD market range (Benchmark: ₹380.00/bags).",
                },
                {
                    "item_name": "Coarse Aggregate 20mm",
                    "category": "aggregate",
                    "quantity": 70,
                    "unit": "cu.m",
                    "claimed_unit_price": 1200.0,
                    "total_amount": 84000.0,
                    "benchmark_unit_price": 1200.0,
                    "deviation_pct": 0.0,
                    "status": "normal",
                    "notes": "Rate is within standard CPWD market range (Benchmark: ₹1,200.00/cu.m).",
                },
                {
                    "item_name": "River Sand Coarse",
                    "category": "sand",
                    "quantity": 50,
                    "unit": "cu.m",
                    "claimed_unit_price": 1800.0,
                    "total_amount": 90000.0,
                    "benchmark_unit_price": 1800.0,
                    "deviation_pct": 0.0,
                    "status": "normal",
                    "notes": "Rate is within standard CPWD market range (Benchmark: ₹1,800.00/cu.m).",
                },
            ],
            overall_deviation_pct=0.62,
            anomaly_score=0.8,
            fraud_risk_level="LOW",
            ai_analysis_summary="✅ CLEAN PROCUREMENT AUDIT (Score: 0.8/100): All invoiced material rates align closely with standard CPWD and State Schedule of Rates benchmarks.",
            status=ExpenseBillStatus.VERIFIED,
        )

        bill_fraud = ExpenseBill(
            bill_code="BILL-0147-001",
            project_id=proj_a.id,
            inspector_user_id=inspector1.id,
            vendor_name="Sri Balaji Steel Traders & Suppliers",
            invoice_number="INV-2025-9844",
            bill_date=_days_ago(12),
            total_amount=985000.0,
            items=[
                {
                    "item_name": "TMT Bar Steel Fe500D",
                    "category": "steel_tmt",
                    "quantity": 5000,
                    "unit": "kg",
                    "claimed_unit_price": 112.0,
                    "total_amount": 560000.0,
                    "benchmark_unit_price": 62.0,
                    "deviation_pct": 80.65,
                    "status": "fraud_risk",
                    "notes": "🚨 Critical Price Anomaly: 80.6% escalation over market benchmark (₹62.00/kg). Potential over-invoicing fraud.",
                },
                {
                    "item_name": "Grade 53 OPC Cement",
                    "category": "cement",
                    "quantity": 500,
                    "unit": "bags",
                    "claimed_unit_price": 610.0,
                    "total_amount": 305000.0,
                    "benchmark_unit_price": 380.0,
                    "deviation_pct": 60.53,
                    "status": "fraud_risk",
                    "notes": "🚨 Critical Price Anomaly: 60.5% escalation over market benchmark (₹380.00/bags). Potential over-invoicing fraud.",
                },
                {
                    "item_name": "Kiln Burnt Red Clay Bricks",
                    "category": "bricks",
                    "quantity": 10000,
                    "unit": "pieces",
                    "claimed_unit_price": 12.0,
                    "total_amount": 120000.0,
                    "benchmark_unit_price": 8.50,
                    "deviation_pct": 41.18,
                    "status": "severe_inflation",
                    "notes": "⚠️ Severe price inflation: 41.2% above standard rate (₹8.50/pieces). Flagged for audit.",
                },
            ],
            overall_deviation_pct=69.61,
            anomaly_score=88.4,
            fraud_risk_level="CRITICAL",
            ai_analysis_summary="🚨 CRITICAL FINANCIAL FRAUD RISK (Score: 88.4/100): Significant material rate escalation detected with overall 69.6% price inflation. 3 line items severely exceed CPWD/Schedule of Rates benchmarks. Immediate forensic verification recommended.",
            status=ExpenseBillStatus.FLAGGED,
        )

        db.add_all([bill_clean, bill_fraud])

        await db.commit()
        print("✓ Database seeded successfully with demo data.")
        print("  Accounts:")
        print("    Admin:     admin@satark.gov.in / admin123")
        print("    Inspector: inspector1@satark.gov.in / inspector123  (INS-0042)")
        print("    Inspector: inspector2@satark.gov.in / inspector123  (INS-0078)")
        print("    Inspector: inspector3@satark.gov.in / inspector123  (INS-0105)")
        print("    Officer:   officer@satark.gov.in / officer123")
        print("    Auditor:   auditor@satark.gov.in / auditor123")


if __name__ == "__main__":
    asyncio.run(seed())
