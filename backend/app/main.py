"""SATARK-MPLADS — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import engine, Base

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (dev convenience; use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Evidence-driven MPLADS monitoring and fraud/anomaly detection platform",
    lifespan=lifespan,
)

# CORS
cors_origins = settings.cors_origins_list
if "*" in cors_origins or settings.CORS_ORIGINS == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?:\/\/.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Ensure and mount evidence storage for serving images (in development)
evidence_dir = settings.evidence_storage
evidence_dir.mkdir(parents=True, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=str(evidence_dir)), name="evidence")

# Register routers
from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router
from app.api.routes.projects import router as projects_router
from app.api.routes.assignments import router as assignments_router
from app.api.routes.inspections import router as inspections_router
from app.api.routes.alerts_audit import alerts_router, audit_router, timeline_router, dashboard_router
from app.api.routes.ai import router as ai_router
from app.api.routes.summons import router as summons_router
from app.api.routes.bills import router as bills_router

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(projects_router)
app.include_router(assignments_router)
app.include_router(inspections_router)
app.include_router(alerts_router)
app.include_router(audit_router)
app.include_router(timeline_router)
app.include_router(dashboard_router)
app.include_router(ai_router)
app.include_router(summons_router)
app.include_router(bills_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# Mount Static Next.js Frontend (Static Export)
frontend_out = Path(__file__).resolve().parent.parent.parent / "frontend" / "out"
if not frontend_out.exists():
    frontend_out = Path(__file__).resolve().parent.parent / "out"
if not frontend_out.exists():
    frontend_out = Path("out")

if frontend_out.exists() and (frontend_out / "index.html").exists():
    _next_dir = frontend_out / "_next"
    if _next_dir.exists():
        app.mount("/_next", StaticFiles(directory=str(_next_dir)), name="next_static")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_frontend(full_path: str):
        # Allow FastAPI API routes and docs to pass through
        if full_path.startswith("api/") or full_path.startswith("evidence/") or full_path in ("docs", "openapi.json", "redoc"):
            raise HTTPException(status_code=404, detail="Not Found")

        target = frontend_out / full_path
        if target.is_file():
            return FileResponse(target)

        target_html = frontend_out / f"{full_path}.html"
        if target_html.is_file():
            return FileResponse(target_html)

        target_index = target / "index.html"
        if target_index.is_file():
            return FileResponse(target_index)

        if full_path.startswith("projects/"):
            sample_project = frontend_out / "projects" / "1.html"
            if sample_project.is_file():
                return FileResponse(sample_project)

        index_file = frontend_out / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)

        return FileResponse(frontend_out / "404.html")

