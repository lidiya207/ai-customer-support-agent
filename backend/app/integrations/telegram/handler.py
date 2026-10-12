"""Handle Telegram messages with the same agent + persistence as web chat."""

from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_support_agent
from app.integrations.telegram.identity import get_or_create_telegram_user
from app.models.conversation import (
    Conversation,
    ConversationStatus,
    Message,
    MessageSender,
)
from app.services import persistence
from app.services.llm_service import LLMServiceError

_HANDOFF_FIRST = (
    "A human support agent is handling this conversation now. "
    "You can keep writing here — they will see your messages and reply."
)
_HANDOFF_ACK = "Message received. Waiting for the support agent to reply."

WELCOME = (
    "Hi! I'm the AI customer support assistant.\n\n"
    "Ask about orders, shipping, billing, accounts, or open a ticket.\n\n"
    "Commands:\n"
    "/help — show this message\n"
    "/new — start a fresh conversation"
)

HELP = WELCOME


@dataclass
class TelegramReply:
    text: str
    intent: str | None = None
    escalated: bool = False
    ticket_id: str | None = None
    conversation_id: str | None = None


def _already_notified_handoff(db: Session, conversation_id: str) -> bool:
    rows = db.scalars(
        select(Message).where(
            Message.conversation_id == conversation_id,
            Message.sender_type == MessageSender.system,
        )
    )
    for msg in rows:
        content = (msg.content or "").lower()
        if "support agent" in content or "ai auto-replies" in content:
            return True
        if "message received" in content or "delivered to the support" in content:
            return True
        if msg.meta_json and "human_handoff" in msg.meta_json:
            return True
    return False


def _handle_paused_ai(db: Session, *, conversation_id: str) -> str:
    if _already_notified_handoff(db, conversation_id):
        return _HANDOFF_ACK
    persistence.add_message(
        db,
        conversation_id=conversation_id,
        sender_type=MessageSender.system,
        content=_HANDOFF_FIRST,
        meta={"intent": "human_handoff", "escalated": True},
    )
    return _HANDOFF_FIRST


def _recent_history(
    db: Session,
    *,
    conversation_id: str,
    limit: int,
) -> list[dict[str, str]]:
    rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).all()
    history: list[dict[str, str]] = []
    for msg in reversed(rows):
        if msg.sender_type == MessageSender.customer:
            history.append({"role": "user", "content": msg.content})
        elif msg.sender_type in (MessageSender.ai, MessageSender.support_agent):
            history.append({"role": "assistant", "content": msg.content})
    return history


def start_new_conversation(db: Session, *, chat_id: int, display_name: str) -> str:
    """Close any active conversation so the next message starts fresh."""
    user = get_or_create_telegram_user(db, chat_id=chat_id, display_name=display_name)
    active = db.scalars(
        select(Conversation).where(
            Conversation.customer_id == user.id,
            Conversation.status.in_(
                [ConversationStatus.active, ConversationStatus.waiting]
            ),
        )
    ).all()
    for conv in active:
        conv.status = ConversationStatus.closed
    db.commit()
    return "Started a new conversation. Send your question whenever you're ready."


async def handle_user_message(
    db: Session,
    *,
    chat_id: int,
    display_name: str,
    text: str,
    history_limit: int = 12,
) -> TelegramReply:
    """Process one customer message and return the bot reply text."""
    message = text.strip()
    if not message:
        return TelegramReply(text="Please send a text message.")

    user = get_or_create_telegram_user(db, chat_id=chat_id, display_name=display_name)
    conversation = persistence.get_or_create_conversation(
        db,
        customer_id=user.id,
    )
    history = _recent_history(
        db,
        conversation_id=conversation.id,
        limit=history_limit,
    )

    persistence.add_message(
        db,
        conversation_id=conversation.id,
        sender_type=MessageSender.customer,
        content=message,
        sender_id=user.id,
    )

    if not conversation.ai_enabled:
        handoff = _handle_paused_ai(db, conversation_id=conversation.id)
        persistence.notify_customer_message_waiting(
            db,
            conversation=conversation,
            message_preview=message,
        )
        db.commit()
        return TelegramReply(
            text=handoff,
            intent="human_handoff",
            escalated=True,
            conversation_id=conversation.id,
        )

    started = time.perf_counter()
    try:
        result = await run_support_agent(
            message=message,
            customer_id=user.id,
            history=history,
            db=db,
            conversation_id=conversation.id,
        )
    except LLMServiceError as exc:
        db.rollback()
        return TelegramReply(
            text=f"Sorry, I couldn't reach the AI right now ({exc}). Please try again.",
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return TelegramReply(
            text=f"Something went wrong. Please try again in a moment. ({exc})",
        )

    latency_ms = int((time.perf_counter() - started) * 1000)
    persistence.add_message(
        db,
        conversation_id=conversation.id,
        sender_type=MessageSender.ai,
        content=result.response,
        meta={
            "intent": result.intent,
            "tools_used": result.tools_used,
            "escalated": result.escalated,
            "ticket_id": result.ticket_id,
            "channel": "telegram",
        },
    )
    persistence.save_agent_run(
        db,
        customer_id=user.id,
        conversation_id=conversation.id,
        intent=result.intent,
        confidence=result.confidence,
        input_text=message,
        output_text=result.response,
        tools_used=result.tools_used,
        tool_results=result.tool_results,
        escalated=result.escalated,
        ticket_id=result.ticket_id,
        model=result.model,
        latency_ms=latency_ms,
        sources=result.sources,
    )
    db.commit()

    reply = result.response
    if result.escalated and result.ticket_id:
        reply = f"{reply}\n\n(Ticket: {result.ticket_id})"

    return TelegramReply(
        text=reply,
        intent=result.intent,
        escalated=result.escalated,
        ticket_id=result.ticket_id,
        conversation_id=conversation.id,
    )
