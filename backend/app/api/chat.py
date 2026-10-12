import json
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_support_agent, stream_support_agent
from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.conversation import Message, MessageSender
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, KnowledgeSource
from app.services import persistence
from app.services.llm_service import LLMServiceError

router = APIRouter(prefix="/api", tags=["chat"])

_HANDOFF_FIRST = (
    "A human support agent is handling this conversation now. "
    "You can keep writing here — they will see your messages and reply in this chat."
)
_HANDOFF_ACK = "Message received. Waiting for the support agent to reply in this chat."


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _already_notified_handoff(db: Session, conversation_id: str) -> bool:
    """Check DB directly so we don't rely on a stale messages relationship."""
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


def _handle_paused_ai_chat(
    db: Session,
    *,
    conversation_id: str,
) -> tuple[str, bool]:
    """
    Returns (reply_text, persisted_system_notice).

    First handoff notice is stored once. Later customer messages are stored,
    but we do NOT spam another System activity row — only a light ephemeral ack.
    """
    if _already_notified_handoff(db, conversation_id):
        return _HANDOFF_ACK, False

    persistence.add_message(
        db,
        conversation_id=conversation_id,
        sender_type=MessageSender.system,
        content=_HANDOFF_FIRST,
        meta={"intent": "human_handoff", "escalated": True},
    )
    return _HANDOFF_FIRST, True


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Run the agentic support flow and persist conversation + agent run."""
    history = [
        {"role": item.role, "content": item.content.strip()}
        for item in request.history
        if item.content.strip()
    ]

    conversation = persistence.get_or_create_conversation(
        db,
        customer_id=current_user.id,
        conversation_id=request.conversation_id,
    )
    persistence.add_message(
        db,
        conversation_id=conversation.id,
        sender_type=MessageSender.customer,
        content=request.message.strip(),
        sender_id=current_user.id,
    )

    # Human handoff: AI paused after escalation / claim.
    if not conversation.ai_enabled:
        handoff, _ = _handle_paused_ai_chat(db, conversation_id=conversation.id)
        persistence.notify_customer_message_waiting(
            db,
            conversation=conversation,
            message_preview=request.message,
        )
        db.commit()
        return ChatResponse(
            response=handoff,
            model=None,
            intent="human_handoff",
            confidence=1.0,
            tools_used=[],
            sources=[],
            escalated=True,
            ticket_id=None,
            conversation_id=conversation.id,
        )

    started = time.perf_counter()
    try:
        result = await run_support_agent(
            message=request.message.strip(),
            customer_id=current_user.id,
            history=history,
            db=db,
            conversation_id=conversation.id,
        )
    except LLMServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

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
        },
    )
    persistence.save_agent_run(
        db,
        customer_id=current_user.id,
        conversation_id=conversation.id,
        intent=result.intent,
        confidence=result.confidence,
        input_text=request.message.strip(),
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

    return ChatResponse(
        response=result.response,
        model=result.model,
        intent=result.intent,
        confidence=result.confidence,
        tools_used=result.tools_used,
        sources=[KnowledgeSource(**source) for source in result.sources],
        escalated=result.escalated,
        ticket_id=result.ticket_id,
        conversation_id=conversation.id,
    )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream an agentic reply as Server-Sent Events (status → tokens → done)."""
    history = [
        {"role": item.role, "content": item.content.strip()}
        for item in request.history
        if item.content.strip()
    ]
    message = request.message.strip()

    conversation = persistence.get_or_create_conversation(
        db,
        customer_id=current_user.id,
        conversation_id=request.conversation_id,
    )
    persistence.add_message(
        db,
        conversation_id=conversation.id,
        sender_type=MessageSender.customer,
        content=message,
        sender_id=current_user.id,
    )
    db.flush()

    async def event_generator() -> AsyncIterator[str]:
        started = time.perf_counter()
        yield _sse(
            "meta",
            {
                "conversation_id": conversation.id,
                "status": "thinking",
            },
        )

        if not conversation.ai_enabled:
            handoff, _ = _handle_paused_ai_chat(
                db, conversation_id=conversation.id
            )
            persistence.notify_customer_message_waiting(
                db,
                conversation=conversation,
                message_preview=message,
            )
            db.commit()
            yield _sse(
                "status",
                {
                    "intent": "human_handoff",
                    "confidence": 1.0,
                    "tools_used": [],
                    "escalated": True,
                    "ticket_id": None,
                    "model": None,
                    "conversation_id": conversation.id,
                },
            )
            yield _sse("token", {"content": handoff})
            yield _sse(
                "done",
                {
                    "response": handoff,
                    "model": None,
                    "intent": "human_handoff",
                    "confidence": 1.0,
                    "tools_used": [],
                    "sources": [],
                    "escalated": True,
                    "ticket_id": None,
                    "conversation_id": conversation.id,
                },
            )
            return

        final: dict | None = None
        try:
            async for event in stream_support_agent(
                message=message,
                customer_id=current_user.id,
                history=history,
                db=db,
                conversation_id=conversation.id,
            ):
                event_type = event.get("type")
                if event_type == "status":
                    yield _sse(
                        "status",
                        {
                            "intent": event.get("intent"),
                            "confidence": event.get("confidence"),
                            "tools_used": event.get("tools_used") or [],
                            "escalated": event.get("escalated", False),
                            "ticket_id": event.get("ticket_id"),
                            "model": event.get("model"),
                            "conversation_id": conversation.id,
                        },
                    )
                elif event_type == "token":
                    yield _sse("token", {"content": event.get("content") or ""})
                elif event_type == "done":
                    final = event
        except LLMServiceError as exc:
            db.rollback()
            yield _sse("error", {"detail": str(exc), "status_code": exc.status_code})
            return
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            yield _sse("error", {"detail": str(exc) or "Agent stream failed."})
            return

        if final is None:
            db.rollback()
            yield _sse("error", {"detail": "No response generated."})
            return

        latency_ms = int((time.perf_counter() - started) * 1000)
        response_text = str(final.get("response") or "")
        tools_used = list(final.get("tools_used") or [])
        sources = list(final.get("sources") or [])
        escalated = bool(final.get("escalated"))
        ticket_id = final.get("ticket_id")
        intent = str(final.get("intent") or "general_question")
        confidence = float(final.get("confidence") or 0.0)
        model = final.get("model")
        tool_results = list(final.get("tool_results") or [])

        persistence.add_message(
            db,
            conversation_id=conversation.id,
            sender_type=MessageSender.ai,
            content=response_text,
            meta={
                "intent": intent,
                "tools_used": tools_used,
                "escalated": escalated,
                "ticket_id": ticket_id,
            },
        )
        persistence.save_agent_run(
            db,
            customer_id=current_user.id,
            conversation_id=conversation.id,
            intent=intent,
            confidence=confidence,
            input_text=message,
            output_text=response_text,
            tools_used=tools_used,
            tool_results=tool_results,
            escalated=escalated,
            ticket_id=ticket_id,
            model=model,
            latency_ms=latency_ms,
            sources=sources,
        )
        db.commit()

        yield _sse(
            "done",
            {
                "response": response_text,
                "model": model,
                "intent": intent,
                "confidence": confidence,
                "tools_used": tools_used,
                "sources": sources,
                "escalated": escalated,
                "ticket_id": ticket_id,
                "conversation_id": conversation.id,
            },
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
