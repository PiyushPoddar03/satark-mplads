"""Audit logging service — append-only event recording."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditLog, User


async def log_audit(
    db: AsyncSession,
    *,
    actor: User | None = None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    description: str | None = None,
    previous_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Create an audit log entry. Should never raise — fire and forget."""
    log = AuditLog(
        actor_id=actor.id if actor else None,
        actor_role=actor.role.value if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        previous_value=previous_value,
        new_value=new_value,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    return log
