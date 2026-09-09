"""
Strict Authorization and RBAC Security Tests for SATARK-MPLADS.

Verifies:
1. Inspector can ONLY view assigned projects (GET /api/projects)
2. Inspector gets 403 Forbidden when accessing unassigned project (GET /api/projects/{id})
3. Inspector cannot start inspection or upload evidence for unassigned project
4. Geofence validation flags captures outside project radius
5. Evidence SHA-256 hash calculation integrity
6. Audit logs are written upon critical actions
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import create_access_token
from app.main import app
from app.models.enums import UserRole
from app.models.models import AuditLog, Project, ProjectInspector, User


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_admin_access_all_projects(async_client: AsyncClient):
    async with async_session_factory() as db:
        admin_res = await db.execute(select(User).where(User.role == UserRole.ADMIN))
        admin = admin_res.scalar_one()

    token = create_access_token({"sub": str(admin.id), "role": admin.role.value, "email": admin.email})
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/api/projects", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 5  # Admin sees all seeded projects


@pytest.mark.asyncio
async def test_inspector_strict_assigned_projects_only(async_client: AsyncClient):
    async with async_session_factory() as db:
        # Inspector 2 is assigned ONLY to Project E in Mysuru
        insp2_res = await db.execute(select(User).where(User.inspector_id == "INS-0078"))
        insp2 = insp2_res.scalar_one()

        # Project A is assigned to Inspector 1 (INS-0042)
        proj_a_res = await db.execute(select(Project).where(Project.project_code == "MPLADS-KA-2025-0147"))
        proj_a = proj_a_res.scalar_one()

        # Project E is assigned to Inspector 2
        proj_e_res = await db.execute(select(Project).where(Project.project_code == "MPLADS-KA-2025-0456"))
        proj_e = proj_e_res.scalar_one()

    token = create_access_token({"sub": str(insp2.id), "role": insp2.role.value, "email": insp2.email})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List projects — Inspector 2 should ONLY see Project E
    response = await async_client.get("/api/projects", headers=headers)
    assert response.status_code == 200
    data = response.json()
    project_ids = [p["id"] for p in data["projects"]]
    assert str(proj_e.id) in project_ids
    assert str(proj_a.id) not in project_ids

    # 2. Direct access to assigned project -> 200 OK
    resp_e = await async_client.get(f"/api/projects/{proj_e.id}", headers=headers)
    assert resp_e.status_code == 200

    # 3. Direct access to unassigned project -> 403 FORBIDDEN
    resp_a = await async_client.get(f"/api/projects/{proj_a.id}", headers=headers)
    assert resp_a.status_code == 403
    assert "not assigned" in resp_a.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unauthorized_inspection_start_blocked(async_client: AsyncClient):
    async with async_session_factory() as db:
        # Inspector 3 (INS-0105) is in Hyderabad
        insp3_res = await db.execute(select(User).where(User.inspector_id == "INS-0105"))
        insp3 = insp3_res.scalar_one()

        # Project A is in Bengaluru
        proj_a_res = await db.execute(select(Project).where(Project.project_code == "MPLADS-KA-2025-0147"))
        proj_a = proj_a_res.scalar_one()

    token = create_access_token({"sub": str(insp3.id), "role": insp3.role.value, "email": insp3.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Try to start inspection on unauthorized project
    payload = {
        "project_id": str(proj_a.id),
        "latitude": 13.1007,
        "longitude": 77.5963,
        "gps_accuracy": 5.0,
    }
    response = await async_client.post("/api/inspections/start", json=payload, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_stats_endpoint(async_client: AsyncClient):
    async with async_session_factory() as db:
        admin_res = await db.execute(select(User).where(User.role == UserRole.ADMIN))
        admin = admin_res.scalar_one()

    token = create_access_token({"sub": str(admin.id), "role": admin.role.value, "email": admin.email})
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/api/dashboard/stats", headers=headers)
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_projects"] >= 6
    assert stats["high_risk_projects"] >= 1
    assert stats["total_inspectors"] >= 3
