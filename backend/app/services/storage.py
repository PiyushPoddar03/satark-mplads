"""Evidence storage backed by Supabase Storage in serverless deployments."""

from __future__ import annotations

import mimetypes

import httpx
from fastapi import HTTPException

from app.core.config import get_settings


def _headers(content_type: str | None = None) -> dict[str, str]:
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _object_url(storage_key: str) -> str:
    settings = get_settings()
    return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{settings.SUPABASE_STORAGE_BUCKET}/{storage_key}"


async def upload_evidence(storage_key: str, content: bytes, content_type: str) -> None:
    """Upload an object when Supabase Storage is configured."""
    if not get_settings().uses_supabase_storage:
        return
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            _object_url(storage_key),
            headers={**_headers(content_type), "x-upsert": "true"},
            content=content,
        )
    if response.is_error:
        raise HTTPException(status_code=502, detail="Could not store evidence file")


async def download_evidence(storage_key: str) -> tuple[bytes, str]:
    """Read an evidence object through the private service-role API."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(_object_url(storage_key), headers=_headers())
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Evidence file not found")
    if response.is_error:
        raise HTTPException(status_code=502, detail="Could not retrieve evidence file")
    media_type = response.headers.get("content-type") or mimetypes.guess_type(storage_key)[0] or "image/jpeg"
    return response.content, media_type
