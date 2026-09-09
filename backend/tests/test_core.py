"""Unit and security authorization tests for SATARK-MPLADS."""

from __future__ import annotations

import pytest
from app.utils.geo import haversine_distance, is_within_geofence
from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hashing():
    pwd = "secret_password_123"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_token_flow():
    payload = {"sub": "user-1234", "role": "admin", "email": "test@satark.gov.in"}
    token = create_access_token(payload)
    assert token is not None

    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-1234"
    assert decoded["role"] == "admin"
    assert decoded["type"] == "access"


def test_geofence_calculation():
    # Exact center point
    within, dist = is_within_geofence(13.1007, 77.5963, 13.1007, 77.5963, 100)
    assert within is True
    assert dist == 0.0

    # Within 100m geofence (~50m away)
    within, dist = is_within_geofence(13.1007, 77.5963, 13.1011, 77.5963, 100)
    assert within is True
    assert dist < 100

    # Far away (~2.3km away)
    within, dist = is_within_geofence(13.1007, 77.5963, 13.1207, 77.5963, 100)
    assert within is False
    assert dist > 2000


@pytest.mark.asyncio
async def test_ai_mock_providers():
    from app.providers.mock import (
        MockFinancialAnomalyProvider,
        MockImageForensicsProvider,
        MockRiskEngineProvider,
        MockSimilarityProvider,
    )

    # 1. Forensics
    forensics = MockImageForensicsProvider()
    clean_res = await forensics.analyze_image("clean_image.jpg")
    assert clean_res.risk_score < 30
    assert clean_res.risk_level == "low"

    susp_res = await forensics.analyze_image("suspicious_image.jpg", {"force_suspicious": True})
    assert susp_res.risk_score > 70
    assert susp_res.risk_level == "high"

    # 2. Financial Anomaly (Decoupling: 42% physical vs 91% financial)
    financial = MockFinancialAnomalyProvider()
    fin_res = await financial.evaluate_financials(
        sanction_amount=4500000,
        released_amount=4200000,
        expenditure=4095000,
        physical_progress=42,
        financial_progress=91,
        project_type="hospital",
        district="Bengaluru Urban",
    )
    assert fin_res.is_decoupled is True
    assert fin_res.progress_expenditure_gap == 49.0
    assert fin_res.risk_score > 60

    # 3. Composite Risk Engine
    risk_engine = MockRiskEngineProvider()
    composite = await risk_engine.calculate_risk(
        image_forensics=susp_res,
        similarity=None,
        financial=fin_res,
        satellite=None,
        geofence_passed=False,
        distance_from_site_m=2300,
        gps_accuracy_m=45,
        contractor_history={"high_risk_projects_count": 2},
    )
    assert composite.overall_score >= 70  # High risk scenario
    assert composite.risk_level in ("high", "critical")
    assert len(composite.explanation_points) > 0


@pytest.mark.asyncio
async def test_evidence_file_serving():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.core.config import get_settings

    settings = get_settings()
    test_storage_dir = settings.evidence_storage / "test_proj"
    test_storage_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_storage_dir / "test_image.jpg"

    # 1x1 pixel test JPEG header
    fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xd9"
    with open(test_file, "wb") as f:
        f.write(fake_jpeg)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/inspections/evidence-file/test_proj/test_image.jpg")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert response.content == fake_jpeg

        # Test non-existent file returns 404
        not_found = await ac.get("/api/inspections/evidence-file/test_proj/non_existent.jpg")
        assert not_found.status_code == 404

