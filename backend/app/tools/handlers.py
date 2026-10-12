"""Executable agent tools. The model never runs arbitrary code — only these."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.rag.knowledge import search_knowledge
from app.services import persistence
from app.tools import store
from app.tools.web_search import search_web


def search_knowledge_base(
    query: str,
    limit: int = 3,
    *,
    db: Session | None = None,
) -> dict[str, Any]:
    results = search_knowledge(query, limit=limit, db=db)
    return {"ok": True, "count": len(results), "results": results}


async def search_internet(query: str, limit: int = 3) -> dict[str, Any]:
    """Look up public information on the internet."""
    return await search_web(query, limit=limit)


def get_order_status(order_id: str) -> dict[str, Any]:
    order = store.get_order(order_id)
    if order is None:
        return {
            "ok": False,
            "error": f"Order '{order_id}' was not found.",
            "hint": "Try demo orders 45231, 45321, or 10001.",
        }
    return {"ok": True, "order": order}


def get_subscription() -> dict[str, Any]:
    return {"ok": True, "subscription": store.get_subscription()}


def get_ticket_status(
    *,
    customer_id: str,
    ticket_code: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    """Look up one ticket or list the customer's recent tickets."""
    if db is None:
        return {
            "ok": False,
            "error": "Ticket lookup requires a database connection.",
        }

    if ticket_code:
        ticket = persistence.get_ticket_by_code(
            db, ticket_code=ticket_code, customer_id=customer_id
        )
        if ticket is None:
            return {
                "ok": False,
                "error": f"Ticket '{ticket_code}' was not found for your account.",
            }
        return {
            "ok": True,
            "ticket": {
                "ticket_id": ticket.ticket_code,
                "title": ticket.title,
                "status": ticket.status.value,
                "priority": ticket.priority.value,
                "category": ticket.category,
                "assigned_to": ticket.assigned_agent or "Unassigned",
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            },
        }

    rows = persistence.list_tickets_for_customer(db, customer_id=customer_id, limit=5)
    return {
        "ok": True,
        "count": len(rows),
        "tickets": [
            {
                "ticket_id": t.ticket_code,
                "title": t.title,
                "status": t.status.value,
                "priority": t.priority.value,
                "category": t.category,
                "assigned_to": t.assigned_agent or "Unassigned",
            }
            for t in rows
        ],
    }


def create_support_ticket(
    *,
    customer_id: str,
    title: str,
    description: str,
    category: str = "general",
    priority: str = "medium",
    conversation_id: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    if db is not None:
        ticket = persistence.create_ticket(
            db,
            customer_id=customer_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            conversation_id=conversation_id,
        )
        return {
            "ok": True,
            "ticket": {
                "ticket_id": ticket.ticket_code,
                "id": ticket.id,
                "customer_id": ticket.customer_id,
                "title": ticket.title,
                "description": ticket.description,
                "priority": ticket.priority.value,
                "category": ticket.category,
                "status": ticket.status.value,
            },
        }

    ticket = store.create_ticket(
        customer_id=customer_id,
        title=title,
        description=description,
        category=category,
        priority=priority,
        conversation_id=conversation_id,
    )
    return {"ok": True, "ticket": ticket}


def escalate_to_human(
    *,
    customer_id: str,
    reason: str,
    message: str,
    conversation_id: str | None = None,
    create_ticket: bool = True,
    db: Session | None = None,
) -> dict[str, Any]:
    ticket_payload = None
    ticket_db_id = None
    if create_ticket:
        ticket_result = create_support_ticket(
            customer_id=customer_id,
            title=f"Escalation: {reason}",
            description=message,
            category="escalation",
            priority="high",
            conversation_id=conversation_id,
            db=db,
        )
        ticket_payload = ticket_result.get("ticket")
        ticket_db_id = ticket_payload.get("id") if ticket_payload else None

    if db is not None:
        escalation = persistence.create_escalation(
            db,
            customer_id=customer_id,
            reason=reason,
            message=message,
            conversation_id=conversation_id,
            ticket_id=ticket_db_id,
        )
        return {
            "ok": True,
            "escalation": {
                "escalation_id": escalation.escalation_code,
                "reason": escalation.reason,
                "status": escalation.status,
                "ticket_id": ticket_payload.get("ticket_id") if ticket_payload else None,
            },
            "ticket": ticket_payload,
        }

    escalation = store.escalate_conversation(
        customer_id=customer_id,
        reason=reason,
        message=message,
        ticket_id=ticket_payload.get("ticket_id") if ticket_payload else None,
    )
    return {"ok": True, "escalation": escalation, "ticket": ticket_payload}
