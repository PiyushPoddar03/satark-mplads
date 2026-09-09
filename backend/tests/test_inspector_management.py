"""Tests for Inspector Management and District Officer Approval Workflow."""

from __future__ import annotations

import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import create_access_token
from app.main import app
from app.models.enums import UserRole
from app.models.models import User


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_district_officer_inspector_request_lifecycle(async_client: AsyncClient):
    async with async_session_factory() as db:
        # Get admin user
        admin_res = await db.execute(select(User).where(User.role == UserRole.ADMIN))
        admin = admin_res.scalar_one()

        # Get district officer
        officer_res = await db.execute(select(User).where(User.role == UserRole.DISTRICT_OFFICER))
        officer = officer_res.scalar_one()

    admin_token = create_access_token({"sub": str(admin.id), "role": admin.role.value, "email": admin.email})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    officer_token = create_access_token({"sub": str(officer.id), "role": officer.role.value, "email": officer.email})
    officer_headers = {"Authorization": f"Bearer {officer_token}"}

    uid = uuid.uuid4().hex[:6]
    # 1. District Officer submits an "ADD" inspector request
    add_req_payload = {
        "request_type": "add",
        "inspector_data": {
            "full_name": f"Ravi Shankar Prasad {uid}",
            "email": f"ravi.prasad.{uid}@satark.gov.in",
            "inspector_id": f"INS-TEST-{uid.upper()}",
            "phone": "+91 98451 99887",
            "password": "Password@123",
            "state": "Karnataka",
            "district": "Bengaluru Urban",
        },
        "reason": "Additional field capacity needed for rural road projects.",
    }

    resp = await async_client.post("/api/users/inspector-requests", json=add_req_payload, headers=officer_headers)
    assert resp.status_code == 201
    add_req_data = resp.json()
    assert add_req_data["status"] == "pending"
    assert add_req_data["request_type"] == "add"
    req_id = add_req_data["id"]

    # 2. Officer can view their requests
    list_resp = await async_client.get("/api/users/inspector-requests", headers=officer_headers)
    assert list_resp.status_code == 200
    req_ids = [r["id"] for r in list_resp.json()]
    assert req_id in req_ids

    # 3. Admin approves the "ADD" request -> creates new inspector user
    approve_resp = await async_client.post(
        f"/api/users/inspector-requests/{req_id}/approve",
        json={"admin_notes": "Approved for rural road surveillance."},
        headers=admin_headers,
    )
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["status"] == "approved"
    assert approved_data["target_inspector_id"] is not None

    created_inspector_id = approved_data["target_inspector_id"]

    # 4. Verify inspector can now be listed in users
    users_resp = await async_client.get("/api/users?role=field_inspector", headers=admin_headers)
    assert users_resp.status_code == 200
    user_ids = [u["id"] for u in users_resp.json()]
    assert created_inspector_id in user_ids

    # 5. District officer submits a "REMOVE" request for this inspector
    remove_req_payload = {
        "request_type": "remove",
        "target_inspector_id": created_inspector_id,
        "inspector_data": {"full_name": f"Ravi Shankar Prasad {uid}"},
        "reason": "Transferring out of district jurisdiction.",
    }
    rem_resp = await async_client.post("/api/users/inspector-requests", json=remove_req_payload, headers=officer_headers)
    assert rem_resp.status_code == 201
    rem_req_id = rem_resp.json()["id"]

    # 6. Admin approves the "REMOVE" request -> deactivates the inspector
    appr_rem = await async_client.post(
        f"/api/users/inspector-requests/{rem_req_id}/approve",
        json={"admin_notes": "Approved deactivation upon transfer."},
        headers=admin_headers,
    )
    assert appr_rem.status_code == 200
    assert appr_rem.json()["status"] == "approved"

    # 7. Check that inspector is completely deleted from the database
    async with async_session_factory() as db:
        purged_user = (await db.execute(select(User).where(User.id == created_inspector_id))).scalar_one_or_none()
        assert purged_user is None


@pytest.mark.asyncio
async def test_admin_direct_delete_user(async_client: AsyncClient):
    async with async_session_factory() as db:
        admin_res = await db.execute(select(User).where(User.role == UserRole.ADMIN))
        admin = admin_res.scalar_one()

    admin_token = create_access_token({"sub": str(admin.id), "role": admin.role.value, "email": admin.email})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    temp_uid = uuid.uuid4().hex[:6]
    # Create temporary inspector
    create_resp = await async_client.post(
        "/api/users",
        json={
            "full_name": "Temporary Inspector",
            "email": f"temp.inspector.{temp_uid}@satark.gov.in",
            "password": "Password@123",
            "role": "field_inspector",
            "inspector_id": f"INS-TEMP-{temp_uid.upper()}",
            "phone": "+91 99999 11111",
            "state": "Karnataka",
            "district": "Bengaluru",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # Admin permanently deletes and purges user
    del_resp = await async_client.delete(f"/api/users/{user_id}", headers=admin_headers)
    assert del_resp.status_code == 200

    # User is completely removed from database
    async with async_session_factory() as db:
        purged = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        assert purged is None

