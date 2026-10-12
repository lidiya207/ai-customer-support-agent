"""Map Telegram chat IDs to customer User rows."""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole


def telegram_email(chat_id: int) -> str:
    return f"telegram_{chat_id}@telegram.local"


def get_or_create_telegram_user(
    db: Session,
    *,
    chat_id: int,
    display_name: str,
) -> User:
    """Find or auto-provision a customer account for this Telegram chat."""
    email = telegram_email(chat_id)
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        name = (display_name or "").strip()
        if name and existing.name != name:
            existing.name = name
            db.flush()
        return existing

    name = (display_name or "").strip() or f"Telegram {chat_id}"
    user = User(
        name=name[:255],
        email=email,
        # Not usable for web login; Telegram is the identity channel.
        password_hash=hash_password(secrets.token_urlsafe(32)),
        role=UserRole.customer,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user
