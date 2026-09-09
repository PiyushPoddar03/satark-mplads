"""
Sanity check script to verify all backend modules import correctly.

Run: python check_modules.py
"""

import sys

def check():
    print("Testing backend module imports...")

    try:
        from app.core.config import get_settings
        print("✓ app.core.config")

        from app.core.security import hash_password, verify_password, create_access_token, decode_token
        print("✓ app.core.security")

        from app.models.enums import UserRole, ProjectStatus, AlertSeverity
        print("✓ app.models.enums")

        from app.models.models import User, Project, Inspection, Evidence, RiskScore, Alert, AuditLog
        print("✓ app.models.models")

        from app.schemas.auth import LoginRequest, TokenResponse, UserOut
        print("✓ app.schemas.auth")

        from app.schemas.project import ProjectCreate, ProjectResponse
        print("✓ app.schemas.project")

        from app.api.deps import get_current_user, require_admin, require_inspector
        print("✓ app.api.deps")

        from app.utils.geo import haversine_distance, is_within_geofence
        print("✓ app.utils.geo")

        from app.providers.base import ForensicsResult, SimilarityResult, FinancialAnomalyResult
        print("✓ app.providers.base")

        from app.providers.mock import MockImageForensicsProvider, MockSimilarityProvider, MockFinancialAnomalyProvider, MockRiskEngineProvider
        print("✓ app.providers.mock")

        from app.services.ai import analyze_project_evidence, evaluate_project_risk
        print("✓ app.services.ai")

        from app.services.audit import log_audit
        print("✓ app.services.audit")

        from app.main import app
        print("✓ app.main (FastAPI app)")

        print("\n🎉 ALL BACKEND MODULES IMPORTED SUCCESSFULLY!")
        return 0
    except Exception as e:
        print(f"\n❌ Error importing module: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(check())
