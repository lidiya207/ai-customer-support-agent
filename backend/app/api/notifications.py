"""In-app notification APIs for the support/admin dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_support_or_admin
from app.database.session import get_db
from app.models.user import User
from app.services import persistence

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _serialize(note) -> dict:
    return {
        "id": note.id,
        "type": note.type,
        "title": note.title,
        "body": note.body,
        "conversationId": note.conversation_id,
        "ticketId": note.ticket_id,
        "isRead": note.is_read,
        "createdAt": note.created_at.isoformat() if note.created_at else None,
    }


@router.get("")
def list_notifications(
    current_user: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    notes = persistence.list_notifications_for_user(db, user_id=current_user.id)
    return [_serialize(note) for note in notes]


@router.get("/unread-count")
def unread_count(
    current_user: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    count = persistence.unread_notification_count(db, user_id=current_user.id)
    return {"count": count}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: str,
    current_user: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    note = persistence.mark_notification_read(
        db, notification_id=notification_id, user_id=current_user.id
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    db.commit()
    return _serialize(note)


@router.post("/read-all")
def mark_all_read(
    current_user: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    updated = persistence.mark_all_notifications_read(db, user_id=current_user.id)
    db.commit()
    return {"updated": updated}
