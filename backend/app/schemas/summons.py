"""Pydantic schemas for inspector summons."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import SummonsStatus


class SummonsCreate(BaseModel):
    project_id: str = Field(..., min_length=1)
    inspector_user_id: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=10, max_length=2000)
    questions: list[str] | None = None


class SummonsResponse(BaseModel):
    response_text: str = Field(..., min_length=10, max_length=5000)
    response_attachments: list[dict] | None = None


class SummonsReview(BaseModel):
    officer_notes: str | None = None
    status: SummonsStatus


class SummonsItem(BaseModel):
    id: str
    summons_code: str
    project_id: str
    project_code: str | None = None
    project_name: str | None = None
    inspector_user_id: str
    inspector_name: str | None = None
    inspector_id: str | None = None
    officer_user_id: str
    officer_name: str | None = None
    reason: str
    questions: list[str] | None = None
    status: str
    response_text: str | None = None
    response_attachments: list[dict] | None = None
    responded_at: str | None = None
    officer_notes: str | None = None
    reviewed_at: str | None = None
    closed_at: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
