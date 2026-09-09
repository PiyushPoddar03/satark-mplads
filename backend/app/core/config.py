"""SATARK-MPLADS application configuration."""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "SATARK-MPLADS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database (defaults to local SQLite for instant zero-dependency execution, override with PostgreSQL in .env)
    DATABASE_URL: str = "sqlite+aiosqlite:///./satark.db"
    DATABASE_URL_SYNC: str = "sqlite:///./satark.db"

    # Auth
    SECRET_KEY: str = "change-this-to-a-random-64-char-hex-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # Storage
    EVIDENCE_STORAGE_PATH: str = "./storage/evidence"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "satark-evidence"

    # Hosting
    SERVERLESS: bool = False

    # AI
    AI_MOCK_MODE: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Supabase displays libpq-style sslmode URLs; asyncpg expects ssl.
        url = url.replace("sslmode=require", "ssl=require")
        return url

    @property
    def evidence_storage(self) -> Path:
        path = Path(self.EVIDENCE_STORAGE_PATH)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def uses_supabase_storage(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_SERVICE_ROLE_KEY)

    model_config = {"env_file": ".env", "case_sensitive": True}


@lru_cache
def get_settings() -> Settings:
    return Settings()
