"""Ticket APIs for the support dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_support_or_admin
from app.database.session import get_db
from app.models.ticket import Ticket, TicketStatus
from app.models.user import User
from app.services import persistence

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


class TicketUpdate(BaseModel):
    status: str | None = None
    assigned_agent: str | None = None


@router.get("/me")
def list_my_tickets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Customer: list my own support tickets."""
    rows = persistence.list_tickets_for_customer(db, customer_id=current_user.id)
    return [
        {
            "id": ticket.ticket_code,
            "customer": current_user.name,
            "category": ticket.category,
            "priority": ticket.priority.value,
            "assignedTo": ticket.assigned_agent or "Unassigned",
            "status": ticket.status.value if ticket.status.value != "closed" else "resolved",
            "createdAt": ticket.created_at.strftime("%b %d, %Y"),
            "title": ticket.title,
            "conversationId": ticket.conversation_id,
        }
        for ticket in rows
    ]


@router.get("")
def list_tickets(
    _: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = persistence.list_tickets(db)
    payload: list[dict] = []
    for ticket in rows:
        name, _ = persistence.customer_name_email(db, ticket.customer_id)
        payload.append(
            {
                "id": ticket.ticket_code,
                "customer": name,
                "category": ticket.category,
                "priority": ticket.priority.value,
                "assignedTo": ticket.assigned_agent or "Unassigned",
                "status": ticket.status.value if ticket.status.value != "closed" else "resolved",
                "createdAt": ticket.created_at.strftime("%b %d, %Y"),
                "title": ticket.title,
                "conversationId": ticket.conversation_id,
            }
        )
    return payload


@router.get("/stats")
def ticket_stats(
    _: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    rows = persistence.list_tickets(db)
    return {
        "open": sum(1 for t in rows if t.status == TicketStatus.open),
        "in_progress": sum(1 for t in rows if t.status == TicketStatus.in_progress),
        "waiting": sum(1 for t in rows if t.status == TicketStatus.waiting),
        "resolved": sum(
            1 for t in rows if t.status in {TicketStatus.resolved, TicketStatus.closed}
        ),
    }


@router.patch("/{ticket_code}")
def update_ticket(
    ticket_code: str,
    body: TicketUpdate,
    _: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    ticket = db.scalar(select(Ticket).where(Ticket.ticket_code == ticket_code))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    if body.status:
        try:
            ticket.status = TicketStatus(body.status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid status.") from exc
    if body.assigned_agent is not None:
        ticket.assigned_agent = body.assigned_agent
    db.commit()
    return {"ok": True, "id": ticket.ticket_code, "status": ticket.status.value}
