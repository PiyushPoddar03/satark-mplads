"""Authentication and authorization dependencies for FastAPI."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.enums import AssignmentStatus, UserRole
from app.models.models import ProjectInspector, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Decode JWT and return the authenticated user."""
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_roles(*roles: UserRole):
    """Dependency factory: restrict endpoint to specific roles."""

    async def _check(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check


# Convenience role dependencies
require_admin = require_roles(UserRole.ADMIN)
require_inspector = require_roles(UserRole.FIELD_INSPECTOR)
require_officer = require_roles(UserRole.DISTRICT_OFFICER)
require_auditor = require_roles(UserRole.AUDITOR)
require_admin_or_officer = require_roles(UserRole.ADMIN, UserRole.DISTRICT_OFFICER)


async def verify_inspector_project_access(
    project_id: str,
    user: User,
    db: AsyncSession,
) -> bool:
    """
    Server-side check: is this inspector assigned to this project?

    Returns True if the user is not an inspector (admins/officers bypass)
    or if an active assignment exists.
    Raises 403 if the inspector is not assigned.
    """
    if user.role != UserRole.FIELD_INSPECTOR:
        return True

    result = await db.execute(
        select(ProjectInspector).where(
            ProjectInspector.project_id == project_id,
            ProjectInspector.inspector_user_id == user.id,
            ProjectInspector.status == AssignmentStatus.ACTIVE,
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this project",
        )
    return True
