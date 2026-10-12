"""Conversation list/detail APIs for the support dashboard and customers."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_support_or_admin
from app.database.session import get_db
from app.models.conversation import Conversation, ConversationStatus, MessageSender
from app.models.user import User
from app.services import persistence

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class AgentReplyRequest(BaseModel):
    content: str = Field(..., min_length=1)


class ConversationUpdate(BaseModel):
    status: str | None = None
    ai_enabled: bool | None = None


def _fmt_dt(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%b %d, %Y %I:%M %p")


def _relative(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat()


def _agent_name(db: Session, agent_id: str | None) -> str | None:
    if not agent_id:
        return None
    agent = db.get(User, agent_id)
    return agent.name if agent else None


def _serialize_list_item(db: Session, conv: Conversation) -> dict:
    name, email = persistence.customer_name_email(db, conv.customer_id)
    msgs = sorted(conv.messages, key=lambda m: m.created_at) if conv.messages else []
    last = msgs[-1].content if msgs else ""
    return {
        "id": conv.id,
        "customer": name,
        "email": email,
        "topic": conv.topic or (conv.last_intent or "Support"),
        "lastMessage": last[:120],
        "intent": conv.last_intent or "unknown",
        "confidence": int(round((conv.last_confidence or 0) * 100)),
        "status": conv.status.value,
        "assignedAgent": _agent_name(db, conv.assigned_agent_id),
        "aiEnabled": bool(conv.ai_enabled),
        "updatedAt": _relative(conv.updated_at),
        "createdAt": _fmt_dt(conv.created_at),
    }


def _message_role(sender_type: str) -> str:
    if sender_type == "ai":
        return "ai"
    if sender_type == "system":
        return "system"
    if sender_type == "support_agent":
        return "support_agent"
    return "customer"


def _is_handoff_system_text(content: str) -> bool:
    lower = (content or "").lower()
    return (
        "ai auto-replies" in lower
        or "support agent is handling" in lower
        or "escalated to a human" in lower
        or "message received" in lower
        or "waiting for the support agent" in lower
        or "delivered to the support agent" in lower
    )


def _serialize_detail(db: Session, conv: Conversation) -> dict:
    name, email = persistence.customer_name_email(db, conv.customer_id)
    runs = persistence.get_conversation_runs(db, conv.id)
    latest = runs[-1] if runs else None

    messages = []
    saw_handoff_notice = False
    for msg in sorted(conv.messages, key=lambda m: m.created_at):
        role = _message_role(msg.sender_type.value)
        # Collapse duplicate handoff "System activity" spam from older builds.
        if role == "system" and _is_handoff_system_text(msg.content):
            if saw_handoff_notice:
                continue
            saw_handoff_notice = True
        meta = None
        if msg.meta_json:
            try:
                raw = json.loads(msg.meta_json)
                tools = list(raw.get("tools_used") or [])
                bits = []
                if tools:
                    bits.append(f"Tools: {', '.join(tools)}")
                if raw.get("escalated"):
                    ticket = raw.get("ticket_id")
                    bits.append(
                        f"Escalated{f' · {ticket}' if ticket else ''}"
                    )
                meta = {
                    "toolName": raw.get("intent"),
                    "toolResult": " · ".join(bits) if bits else None,
                }
            except json.JSONDecodeError:
                meta = None
        messages.append(
            {
                "id": msg.id,
                "role": role,
                "content": msg.content,
                "timestamp": msg.created_at.strftime("%I:%M %p"),
                "meta": meta,
            }
        )

    tools_used: list[str] = []
    knowledge_used: list[str] = []
    timeline = []
    if latest:
        tools_used = [tc.tool_name for tc in latest.tool_calls]
        timeline = [
            {
                "id": tc.id,
                "label": tc.tool_name,
                "description": (tc.output_json or "")[:180],
                "timestamp": tc.created_at.strftime("%I:%M:%S %p"),
            }
            for tc in latest.tool_calls
        ]

    return {
        "id": conv.id,
        "customer": name,
        "email": email,
        "topic": conv.topic or (conv.last_intent or "Support"),
        "lastMessage": messages[-1]["content"] if messages else "",
        "intent": conv.last_intent or "unknown",
        "confidence": int(round((conv.last_confidence or 0) * 100)),
        "status": conv.status.value,
        "assignedAgent": _agent_name(db, conv.assigned_agent_id),
        "aiEnabled": bool(conv.ai_enabled),
        "updatedAt": _relative(conv.updated_at),
        "createdAt": _fmt_dt(conv.created_at),
        "messages": messages,
        "agentDetails": {
            "detectedIntent": latest.intent
            if latest
            else (conv.last_intent or "unknown"),
            "confidence": int(
                round(
                    ((latest.confidence if latest else conv.last_confidence) or 0)
                    * 100
                )
            ),
            "agentStatus": latest.status.value if latest else conv.status.value,
            "knowledgeUsed": knowledge_used,
            "toolsUsed": tools_used,
            "timeline": timeline,
        },
    }


@router.get("/me")
def list_my_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List conversations belonging to the authenticated customer."""
    rows = persistence.list_conversations_for_customer(
        db, customer_id=current_user.id
    )
    return [_serialize_list_item(db, conv) for conv in rows]


@router.post("/me/new")
def start_my_new_conversation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Resolve active threads so the next chat message creates a new conversation."""
    closed = persistence.resolve_active_conversations(
        db, customer_id=current_user.id
    )
    db.commit()
    return {"detail": "New conversation ready.", "closed": closed}


@router.get("/me/{conversation_id}")
def get_my_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Load a conversation only if it belongs to the authenticated customer."""
    conv = persistence.get_conversation(db, conversation_id)
    if conv is None or conv.customer_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return _serialize_detail(db, conv)


@router.delete("/me/{conversation_id}")
def delete_my_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete one of the authenticated customer's conversations."""
    deleted = persistence.delete_conversation_for_customer(
        db, customer_id=current_user.id, conversation_id=conversation_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    db.commit()
    return {"detail": "Conversation deleted."}


@router.get("")
def list_conversations(
    _: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = persistence.list_conversations(db)
    return [_serialize_list_item(db, conv) for conv in rows]


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    _: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    conv = persistence.get_conversation(db, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return _serialize_detail(db, conv)


@router.post("/{conversation_id}/claim")
def claim_conversation(
    conversation_id: str,
    current_user: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Support agent takes ownership; AI auto-replies stop."""
    conv = persistence.get_conversation(db, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    conv.assigned_agent_id = current_user.id
    conv.ai_enabled = False
    if conv.status in {ConversationStatus.active, ConversationStatus.waiting}:
        conv.status = ConversationStatus.escalated

    persistence.add_message(
        db,
        conversation_id=conv.id,
        sender_type=MessageSender.system,
        content=f"{current_user.name} took ownership of this conversation.",
    )
    db.commit()
    return _serialize_detail(db, conv)


@router.post("/{conversation_id}/messages")
def post_agent_reply(
    conversation_id: str,
    body: AgentReplyRequest,
    current_user: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Human support agent reply (AI remains paused while assigned)."""
    conv = persistence.get_conversation(db, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    if not conv.assigned_agent_id:
        conv.assigned_agent_id = current_user.id
    conv.ai_enabled = False
    if conv.status == ConversationStatus.active:
        conv.status = ConversationStatus.escalated

    persistence.add_message(
        db,
        conversation_id=conv.id,
        sender_type=MessageSender.support_agent,
        content=body.content.strip(),
        sender_id=current_user.id,
        meta={"agent_name": current_user.name},
    )
    db.commit()
    return _serialize_detail(db, conv)


@router.patch("/{conversation_id}")
def update_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    current_user: User = Depends(require_support_or_admin),
    db: Session = Depends(get_db),
) -> dict:
    conv = persistence.get_conversation(db, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    if body.status is not None:
        try:
            conv.status = ConversationStatus(body.status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid status.") from exc
        if conv.status in {ConversationStatus.resolved, ConversationStatus.closed}:
            conv.ai_enabled = False

    if body.ai_enabled is not None:
        conv.ai_enabled = body.ai_enabled
        if body.ai_enabled and conv.status == ConversationStatus.escalated:
            conv.status = ConversationStatus.active
            conv.assigned_agent_id = None
            persistence.add_message(
                db,
                conversation_id=conv.id,
                sender_type=MessageSender.system,
                content="AI auto-replies were re-enabled by support.",
                sender_id=current_user.id,
            )

    db.commit()
    return _serialize_detail(db, conv)
