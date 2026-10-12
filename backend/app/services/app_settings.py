"""Load and persist admin-configurable AI / escalation settings."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.settings import AppSetting

DEFAULT_SYSTEM_PROMPT = (
    "You are a friendly AI customer support assistant for a software/product company.\n\n"
    "Primary focus: orders, shipping, billing, subscriptions, accounts, technical "
    "product issues, tickets, and company policies.\n"
    "Answer clearly and concisely. Do not invent company policies or order data.\n"
    "If escalated, tell the customer a human will follow up and include any ticket id."
)

DEFAULTS: dict[str, Any] = {
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "model_override": "",
    "temperature": 0.4,
    "confidence_threshold": 0.6,
    "escalate_refunds": True,
    "escalate_complaints": True,
    "max_failed_tools": 3,
    "workspace_name": "AI Support",
    "support_email": "support@example.com",
}


def get_all_settings(db: Session) -> dict[str, Any]:
    rows = list(db.scalars(select(AppSetting)))
    merged = dict(DEFAULTS)
    for row in rows:
        try:
            merged[row.key] = json.loads(row.value_json)
        except (TypeError, json.JSONDecodeError):
            merged[row.key] = row.value_json
    return merged


def get_setting(db: Session, key: str, default: Any = None) -> Any:
    row = db.get(AppSetting, key)
    if row is None:
        return DEFAULTS.get(key, default)
    try:
        return json.loads(row.value_json)
    except (TypeError, json.JSONDecodeError):
        return row.value_json


def update_settings(db: Session, updates: dict[str, Any]) -> dict[str, Any]:
    allowed = set(DEFAULTS.keys())
    for key, value in updates.items():
        if key not in allowed:
            continue
        row = db.get(AppSetting, key)
        payload = json.dumps(value)
        if row is None:
            db.add(AppSetting(key=key, value_json=payload))
        else:
            row.value_json = payload
    db.commit()
    return get_all_settings(db)
