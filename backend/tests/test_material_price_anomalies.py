"""
Test Material Price Anomaly Detection & Bill Upload Service.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import create_access_token
from app.main import app
from app.models.enums import ExpenseBillStatus, UserRole
from app.models.models import Project, ProjectInspector, User
from app.services.material_prices import (
    analyze_expense_items,
    find_benchmark_for_item,
    get_all_benchmarks,
)


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_material_benchmarks_loaded():
    """Verify standard CPWD benchmarks are defined with valid numeric rates."""
    benchmarks = get_all_benchmarks()
    assert len(benchmarks) >= 10

    cement = find_benchmark_for_item("OPC 53 Grade Cement", "cement")
    assert cement is not None
    assert cement["benchmark_price"] == 380.0
    assert cement["unit"] == "bags"

    steel = find_benchmark_for_item("TMT Rebar Saria Fe500D", "steel_tmt")
    assert steel is not None
    assert steel["benchmark_price"] == 62.0


def test_normal_material_bill_analysis():
    """Test standard market price bill is classified as NORMAL with low anomaly score."""
    normal_items = [
        {
            "item_name": "OPC 53 Grade Cement",
            "category": "cement",
            "quantity": 200,
            "unit": "bags",
            "claimed_unit_price": 385.0,  # +1.3% deviation
        },
        {
            "item_name": "Fe500D TMT Steel Rebar",
            "category": "steel_tmt",
            "quantity": 1500,
            "unit": "kg",
            "claimed_unit_price": 63.5,  # +2.4% deviation
        },
        {
            "item_name": "River Sand Coarse",
            "category": "sand",
            "quantity": 25,
            "unit": "cu.m",
            "claimed_unit_price": 1850.0,  # +2.7% deviation
        },
    ]

    result = analyze_expense_items(normal_items)

    assert result.anomaly_score < 25.0
    assert result.fraud_risk_level in ("LOW", "MODERATE")
    assert result.flagged_items_count == 0
    assert result.recommended_status == ExpenseBillStatus.VERIFIED
    assert len(result.items) == 3
    for item in result.items:
        assert item.status == "normal"


def test_fraudulent_inflated_material_bill_analysis():
    """Test over-invoiced material bill triggers CRITICAL fraud risk and flagged status."""
    fraud_items = [
        {
            "item_name": "OPC 53 Grade Cement",
            "category": "cement",
            "quantity": 500,
            "unit": "bags",
            "claimed_unit_price": 650.0,  # +71.0% deviation (CPWD is 380)
        },
        {
            "item_name": "TMT Bar Steel Fe500D",
            "category": "steel_tmt",
            "quantity": 4000,
            "unit": "kg",
            "claimed_unit_price": 115.0,  # +85.4% deviation (CPWD is 62)
        },
        {
            "item_name": "Red Clay Kiln Bricks",
            "category": "bricks",
            "quantity": 20000,
            "unit": "pieces",
            "claimed_unit_price": 14.50,  # +70.5% deviation (CPWD is 8.5)
        },
    ]

    result = analyze_expense_items(fraud_items)

    assert result.anomaly_score > 60.0
    assert result.fraud_risk_level in ("HIGH", "CRITICAL")
    assert result.flagged_items_count == 3
    assert result.recommended_status == ExpenseBillStatus.FLAGGED
    assert "CRITICAL" in result.ai_summary or "HIGH" in result.ai_summary


@pytest.mark.asyncio
async def test_only_field_inspector_can_upload_expense_bill(async_client: AsyncClient):
    """Verify that only assigned field inspectors can upload bills, while officers/admins are blocked."""
    async with async_session_factory() as db:
        # Get users
        officer = (await db.execute(select(User).where(User.role == UserRole.DISTRICT_OFFICER))).scalar_one()
        inspector = (await db.execute(select(User).where(User.role == UserRole.FIELD_INSPECTOR))).scalars().first()

        # Find an assigned project for the inspector
        assignment = (
            await db.execute(
                select(ProjectInspector).where(ProjectInspector.inspector_user_id == inspector.id)
            )
        ).scalars().first()
        project_id = assignment.project_id

    officer_token = create_access_token({"sub": str(officer.id), "role": officer.role.value, "email": officer.email})
    inspector_token = create_access_token({"sub": str(inspector.id), "role": inspector.role.value, "email": inspector.email})

    bill_payload = {
        "project_id": project_id,
        "vendor_name": "Bharat Steel Suppliers",
        "invoice_number": "INV-TEST-001",
        "items": [
            {
                "item_name": "OPC 53 Grade Cement",
                "category": "cement",
                "quantity": 100,
                "unit": "bags",
                "claimed_unit_price": 380.0,
            }
        ],
    }

    # 1. District Officer attempt -> HTTP 403 Forbidden
    officer_resp = await async_client.post(
        "/api/bills",
        json=bill_payload,
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert officer_resp.status_code == 403
    assert "Only Field Inspectors" in officer_resp.json()["detail"]

    # 2. Assigned Field Inspector attempt -> HTTP 201 Created
    inspector_resp = await async_client.post(
        "/api/bills",
        json=bill_payload,
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert inspector_resp.status_code == 201
    assert inspector_resp.json()["vendor_name"] == "Bharat Steel Suppliers"

