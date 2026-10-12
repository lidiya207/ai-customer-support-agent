"""Admin settings API — system prompt, model override, escalation rules."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_support_or_admin
from app.database.session import get_db
from app.models.user import User
from app.services import app_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    system_prompt: str | None = None
    model_override: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    confidence_threshold: float | None = Field(default=None, ge=0, le=1)
    escalate_refunds: bool | None = None
    escalate_complaints: bool | None = None
    max_failed_tools: int | None = Field(default=None, ge=1, le=10)
    workspace_name: str | None = None
    support_email: str | None = None


@router.get("")
def read_settings(
    _: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return app_settings.get_all_settings(db)


@router.put("")
def write_settings(
    body: SettingsUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    updates = body.model_dump(exclude_none=True)
    return app_settings.update_settings(db, updates)
