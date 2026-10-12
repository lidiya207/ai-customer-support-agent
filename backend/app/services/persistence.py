"""Persist conversations, tickets, knowledge, and agent runs."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.agent_run import AgentRun, AgentRunStatus, ToolCall
from app.models.conversation import (
    Conversation,
    ConversationStatus,
    Message,
    MessageSender,
)
from app.models.notification import Notification
from app.models.ticket import Escalation, Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole


def _code(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def get_or_create_conversation(
    db: Session,
    *,
    customer_id: str,
    conversation_id: str | None = None,
) -> Conversation:
    if conversation_id:
        existing = db.get(Conversation, conversation_id)
        if existing and existing.customer_id == customer_id:
            return existing

    active = db.scalar(
        select(Conversation)
        .where(
            Conversation.customer_id == customer_id,
            Conversation.status.in_(
                [ConversationStatus.active, ConversationStatus.waiting]
            ),
        )
        .order_by(Conversation.updated_at.desc())
    )
    if active is not None:
        return active

    conversation = Conversation(customer_id=customer_id, status=ConversationStatus.active)
    db.add(conversation)
    db.flush()
    return conversation


def add_message(
    db: Session,
    *,
    conversation_id: str,
    sender_type: MessageSender,
    content: str,
    sender_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        sender_type=sender_type,
        sender_id=sender_id,
        content=content,
        meta_json=json.dumps(meta) if meta else None,
    )
    db.add(message)
    db.flush()
    return message


def create_ticket(
    db: Session,
    *,
    customer_id: str,
    title: str,
    description: str,
    category: str = "general",
    priority: str = "medium",
    conversation_id: str | None = None,
) -> Ticket:
    try:
        priority_enum = TicketPriority(priority)
    except ValueError:
        priority_enum = TicketPriority.medium

    ticket = Ticket(
        ticket_code=_code("TCK"),
        customer_id=customer_id,
        conversation_id=conversation_id,
        title=title,
        description=description,
        category=category,
        priority=priority_enum,
        status=TicketStatus.open,
    )
    db.add(ticket)
    db.flush()
    return ticket


def create_escalation(
    db: Session,
    *,
    customer_id: str,
    reason: str,
    message: str,
    conversation_id: str | None = None,
    ticket_id: str | None = None,
) -> Escalation:
    escalation = Escalation(
        escalation_code=_code("ESC"),
        customer_id=customer_id,
        conversation_id=conversation_id,
        ticket_id=ticket_id,
        reason=reason,
        message=message,
        status="escalated",
    )
    db.add(escalation)
    if conversation_id:
        conversation = db.get(Conversation, conversation_id)
        if conversation is not None:
            conversation.status = ConversationStatus.escalated
            # Pause AI auto-replies until a human resolves or re-enables AI.
            conversation.ai_enabled = False
            add_message(
                db,
                conversation_id=conversation.id,
                sender_type=MessageSender.system,
                content=(
                    "This conversation was escalated to a human support agent. "
                    "AI auto-replies are paused. You can keep sending messages here."
                ),
                meta={"intent": "human_handoff", "escalated": True, "reason": reason},
            )
    db.flush()
    customer_name, _ = customer_name_email(db, customer_id)
    notify_support_staff(
        db,
        type="escalation",
        title="Conversation escalated",
        body=f"{customer_name} needs a human · {reason.replace('_', ' ')}",
        conversation_id=conversation_id,
        ticket_id=ticket_id,
    )
    return escalation


def save_agent_run(
    db: Session,
    *,
    customer_id: str,
    conversation_id: str | None,
    intent: str,
    confidence: float,
    input_text: str,
    output_text: str,
    tools_used: list[str],
    tool_results: list[dict[str, Any]],
    escalated: bool,
    ticket_id: str | None,
    model: str | None,
    latency_ms: int,
    sources: list[dict[str, Any]] | None = None,
) -> AgentRun:
    run = AgentRun(
        conversation_id=conversation_id,
        customer_id=customer_id,
        model=model,
        intent=intent,
        confidence=confidence,
        input_text=input_text,
        output_text=output_text,
        status=AgentRunStatus.escalated if escalated else AgentRunStatus.success,
        latency_ms=latency_ms,
        ticket_id=ticket_id,
    )
    db.add(run)
    db.flush()

    for item in tool_results:
        db.add(
            ToolCall(
                agent_run_id=run.id,
                tool_name=str(item.get("tool") or "unknown"),
                input_json=None,
                output_json=json.dumps(item.get("result"), default=str),
                status="ok",
            )
        )

    if conversation_id:
        conversation = db.get(Conversation, conversation_id)
        if conversation is not None:
            conversation.last_intent = intent
            conversation.last_confidence = confidence
            if not conversation.topic:
                conversation.topic = intent.replace("_", " ").title()
            if escalated:
                conversation.status = ConversationStatus.escalated
            conversation.updated_at = datetime.now(timezone.utc)

    db.flush()
    return run


def list_conversations(db: Session, *, limit: int = 50) -> list[Conversation]:
    stmt: Select[tuple[Conversation]] = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def list_conversations_for_customer(
    db: Session, *, customer_id: str, limit: int = 50
) -> list[Conversation]:
    stmt: Select[tuple[Conversation]] = (
        select(Conversation)
        .where(Conversation.customer_id == customer_id)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def get_conversation(db: Session, conversation_id: str) -> Conversation | None:
    return db.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )


def resolve_active_conversations(db: Session, *, customer_id: str) -> int:
    """Mark the customer's active/waiting threads as resolved so a new one can start."""
    rows = list(
        db.scalars(
            select(Conversation).where(
                Conversation.customer_id == customer_id,
                Conversation.status.in_(
                    [ConversationStatus.active, ConversationStatus.waiting]
                ),
            )
        )
    )
    now = datetime.now(timezone.utc)
    for conversation in rows:
        conversation.status = ConversationStatus.resolved
        conversation.resolved_at = now
        conversation.updated_at = now
    db.flush()
    return len(rows)


def delete_conversation_for_customer(
    db: Session, *, customer_id: str, conversation_id: str
) -> bool:
    """Delete a conversation owned by the customer, clearing related FKs first."""
    conversation = get_conversation(db, conversation_id)
    if conversation is None or conversation.customer_id != customer_id:
        return False

    for ticket in db.scalars(
        select(Ticket).where(Ticket.conversation_id == conversation_id)
    ):
        ticket.conversation_id = None

    for escalation in db.scalars(
        select(Escalation).where(Escalation.conversation_id == conversation_id)
    ):
        escalation.conversation_id = None

    for run in db.scalars(
        select(AgentRun).where(AgentRun.conversation_id == conversation_id)
    ):
        run.conversation_id = None

    db.delete(conversation)
    db.flush()
    return True


def get_conversation_runs(db: Session, conversation_id: str) -> list[AgentRun]:
    return list(
        db.scalars(
            select(AgentRun)
            .where(AgentRun.conversation_id == conversation_id)
            .options(selectinload(AgentRun.tool_calls))
            .order_by(AgentRun.created_at.asc())
        )
    )


def list_tickets(db: Session, *, limit: int = 100) -> list[Ticket]:
    return list(
        db.scalars(select(Ticket).order_by(Ticket.created_at.desc()).limit(limit))
    )


def list_tickets_for_customer(
    db: Session, *, customer_id: str, limit: int = 20
) -> list[Ticket]:
    return list(
        db.scalars(
            select(Ticket)
            .where(Ticket.customer_id == customer_id)
            .order_by(Ticket.created_at.desc())
            .limit(limit)
        )
    )


def get_ticket_by_code(
    db: Session, *, ticket_code: str, customer_id: str | None = None
) -> Ticket | None:
    stmt = select(Ticket).where(Ticket.ticket_code == ticket_code.upper())
    if customer_id is not None:
        stmt = stmt.where(Ticket.customer_id == customer_id)
    return db.scalar(stmt)


def list_agent_runs(db: Session, *, limit: int = 50) -> list[AgentRun]:
    return list(
        db.scalars(
            select(AgentRun)
            .options(selectinload(AgentRun.tool_calls))
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
    )


def analytics_overview(db: Session) -> dict[str, Any]:
    total = db.scalar(select(func.count()).select_from(Conversation)) or 0
    escalated = (
        db.scalar(
            select(func.count()).select_from(Conversation).where(
                Conversation.status == ConversationStatus.escalated
            )
        )
        or 0
    )
    resolved = (
        db.scalar(
            select(func.count()).select_from(Conversation).where(
                Conversation.status == ConversationStatus.resolved
            )
        )
        or 0
    )
    open_tickets = (
        db.scalar(
            select(func.count()).select_from(Ticket).where(Ticket.status == TicketStatus.open)
        )
        or 0
    )
    high_priority = (
        db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.status == TicketStatus.open,
                Ticket.priority.in_([TicketPriority.high, TicketPriority.critical]),
            )
        )
        or 0
    )
    ai_resolved = max(total - escalated, 0)
    resolution_rate = f"{(ai_resolved / total * 100):.1f}% resolution rate" if total else "0%"
    escalation_rate = f"{(escalated / total * 100):.1f}% escalation rate" if total else "0%"

    return {
        "totalConversations": total,
        "totalConversationsChange": f"{resolved} resolved",
        "aiResolved": ai_resolved,
        "resolutionRate": resolution_rate,
        "escalated": escalated,
        "escalationRate": escalation_rate,
        "openTickets": open_tickets,
        "highPriority": high_priority,
    }


def customer_name_email(db: Session, customer_id: str) -> tuple[str, str]:
    user = db.get(User, customer_id)
    if user is None:
        return ("Unknown", "")
    return (user.name, user.email)


def _staff_user_ids(db: Session) -> list[str]:
    rows = db.scalars(
        select(User.id).where(
            User.is_active.is_(True),
            User.role.in_([UserRole.support_agent, UserRole.admin]),
        )
    ).all()
    return list(rows)


def notify_support_staff(
    db: Session,
    *,
    type: str,
    title: str,
    body: str,
    conversation_id: str | None = None,
    ticket_id: str | None = None,
    dedupe_unread: bool = False,
) -> list[Notification]:
    """Create an in-app notification for every active support agent and admin."""
    created: list[Notification] = []
    for user_id in _staff_user_ids(db):
        if dedupe_unread and conversation_id:
            existing = db.scalar(
                select(Notification).where(
                    Notification.user_id == user_id,
                    Notification.conversation_id == conversation_id,
                    Notification.type == type,
                    Notification.is_read.is_(False),
                )
            )
            if existing is not None:
                continue
        note = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            conversation_id=conversation_id,
            ticket_id=ticket_id,
            is_read=False,
        )
        db.add(note)
        created.append(note)
    if created:
        db.flush()
    return created


def notify_customer_message_waiting(
    db: Session,
    *,
    conversation: Conversation,
    message_preview: str,
) -> list[Notification]:
    """Alert staff when a customer writes while waiting for a human."""
    customer_name, _ = customer_name_email(db, conversation.customer_id)
    preview = message_preview.strip()
    if len(preview) > 120:
        preview = preview[:117] + "…"
    return notify_support_staff(
        db,
        type="customer_message",
        title="Customer message waiting",
        body=f"{customer_name}: {preview or '(empty message)'}",
        conversation_id=conversation.id,
        dedupe_unread=True,
    )


def list_notifications_for_user(
    db: Session,
    *,
    user_id: str,
    limit: int = 30,
) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        ).all()
    )


def unread_notification_count(db: Session, *, user_id: str) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )


def mark_notification_read(
    db: Session,
    *,
    notification_id: str,
    user_id: str,
) -> Notification | None:
    note = db.get(Notification, notification_id)
    if note is None or note.user_id != user_id:
        return None
    note.is_read = True
    db.flush()
    return note


def mark_all_notifications_read(db: Session, *, user_id: str) -> int:
    notes = list(
        db.scalars(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        ).all()
    )
    for note in notes:
        note.is_read = True
    if notes:
        db.flush()
    return len(notes)
