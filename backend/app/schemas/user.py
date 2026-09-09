"""Pydantic schemas for user management."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr

from app.models.enums import InspectorRequestStatus, InspectorRequestType, UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole
    inspector_id: str | None = None
    phone: str | None = None
    state: str | None = None
    district: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    state: str | None = None
    district: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    inspector_id: str | None = None
    phone: str | None = None
    state: str | None = None
    district: str | None = None
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class InspectorRequestCreate(BaseModel):
    request_type: InspectorRequestType
    target_inspector_id: str | None = None
    inspector_data: dict
    reason: str


class InspectorRequestReview(BaseModel):
    admin_notes: str | None = None


class InspectorRequestResponse(BaseModel):
    id: str
    request_code: str
    request_type: str
    officer_user_id: str
    officer_name: str | None = None
    target_inspector_id: str | None = None
    target_inspector_name: str | None = None
    inspector_data: dict
    reason: str
    status: str
    reviewed_by: str | None = None
    reviewer_name: str | None = None
    admin_notes: str | None = None
    reviewed_at: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

