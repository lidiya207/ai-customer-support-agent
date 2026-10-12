"""Agentic support orchestrator: intent → tools → LLM reply / escalate."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.services.llm_service import (
    LLMServiceError,
    generate_support_response,
    stream_support_response,
)
from app.tools import handlers

logger = logging.getLogger(__name__)

DEFAULT_AGENT_SYSTEM_PROMPT = (
    "You are a friendly AI customer support assistant.\n"
    "Focus: orders, shipping, billing, subscriptions, accounts, tickets, technical issues.\n"
    "Use tool/knowledge results when provided. Answer in 2–4 short sentences.\n"
    "Do not invent policies, prices, or customer data. If unsure, say so.\n"
    "Refuse religion/politics/medical/illegal topics; invite a product question instead."
)

# Kept for backward-compatible imports/tests.
AGENT_SYSTEM_PROMPT = DEFAULT_AGENT_SYSTEM_PROMPT


def _resolve_system_prompt(db: Session | None) -> str:
    if db is None:
        return DEFAULT_AGENT_SYSTEM_PROMPT
    try:
        from app.services.app_settings import get_setting

        prompt = get_setting(db, "system_prompt")
        if isinstance(prompt, str) and prompt.strip():
            return prompt.strip()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to load system prompt from settings")
    return DEFAULT_AGENT_SYSTEM_PROMPT


def _confidence_threshold(db: Session | None) -> float:
    if db is None:
        return 0.6
    try:
        from app.services.app_settings import get_setting

        value = get_setting(db, "confidence_threshold", 0.6)
        return float(value)
    except Exception:  # noqa: BLE001
        return 0.6


@dataclass
class AgentResult:
    response: str
    intent: str
    confidence: float
    tools_used: list[str] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    escalated: bool = False
    ticket_id: str | None = None
    model: str | None = None


@dataclass
class AgentTurn:
    """Prepared agent turn after intent + tools, before LLM generation."""

    intent: str
    confidence: float
    tools_used: list[str]
    tool_results: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    escalated: bool
    ticket_id: str | None
    llm_messages: list[dict[str, str]]
    is_follow_up: bool = False


def _record_tool(
    name: str,
    result: dict[str, Any],
    tools_used: list[str],
    tool_results: list[dict[str, Any]],
) -> None:
    tools_used.append(name)
    tool_results.append({"tool": name, "result": result})


def _ticket_code(result: dict[str, Any]) -> str | None:
    ticket = result.get("ticket")
    if isinstance(ticket, dict):
        return ticket.get("ticket_id")
    return None


def _source_payload(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "document_id": s.get("document_id"),
            "title": s.get("title"),
            "similarity": s.get("similarity"),
        }
        for s in sources
    ]


def _enriched_search_query(
    message: str,
    history: list[dict[str, str]] | None,
    *,
    is_follow_up: bool,
) -> str:
    """Combine the current follow-up with the prior user question for better retrieval."""
    if not is_follow_up or not history:
        return message
    # Long new questions usually stand alone; only blend for short clarifications.
    if len(message.split()) > 12:
        return message
    from app.agents.intent import last_user_message

    prior = last_user_message(history)
    if not prior or prior.lower() == message.lower():
        return message
    # Keep it short for local model / embedding speed.
    return f"{prior[-180:]} — follow-up: {message}"


async def prepare_agent_turn(
    *,
    message: str,
    customer_id: str,
    history: list[dict[str, str]] | None = None,
    db: Session | None = None,
    conversation_id: str | None = None,
) -> AgentTurn:
    """Detect intent and run tools for one customer message."""
    from app.agents.intent import detect_intent

    intent_result = detect_intent(message, history=history)
    intent = intent_result.intent
    confidence = intent_result.confidence
    follow_up = intent_result.is_follow_up
    search_query = _enriched_search_query(
        message, history, is_follow_up=follow_up
    )

    tools_used: list[str] = []
    tool_results: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    escalated = False
    ticket_id: str | None = None

    if intent == "human_support_request":
        result = handlers.escalate_to_human(
            customer_id=customer_id,
            reason="customer_requested_human",
            message=message,
            conversation_id=conversation_id,
            db=db,
        )
        _record_tool("escalate_to_human", result, tools_used, tool_results)
        escalated = True
        ticket_id = _ticket_code(result)

    elif intent == "refund_request":
        escalate_refunds = True
        if db is not None:
            try:
                from app.services.app_settings import get_setting

                escalate_refunds = bool(get_setting(db, "escalate_refunds", True))
            except Exception:  # noqa: BLE001
                escalate_refunds = True
        if escalate_refunds:
            result = handlers.escalate_to_human(
                customer_id=customer_id,
                reason="refund_request",
                message=message,
                conversation_id=conversation_id,
                db=db,
            )
            _record_tool("escalate_to_human", result, tools_used, tool_results)
            escalated = True
            ticket_id = _ticket_code(result)
        else:
            kb = handlers.search_knowledge_base(search_query, db=db)
            _record_tool("search_knowledge_base", kb, tools_used, tool_results)
            sources = list(kb.get("results") or [])

    elif intent == "ticket_status":
        result = handlers.get_ticket_status(
            customer_id=customer_id,
            ticket_code=intent_result.ticket_code,
            db=db,
        )
        _record_tool("get_ticket_status", result, tools_used, tool_results)
        if result.get("ok") and result.get("ticket"):
            ticket_id = result["ticket"].get("ticket_id")

    elif intent == "order_status":
        order_id = intent_result.order_id
        if order_id:
            result = handlers.get_order_status(order_id)
            _record_tool("get_order_status", result, tools_used, tool_results)
            if not result.get("ok"):
                ticket = handlers.create_support_ticket(
                    customer_id=customer_id,
                    title=f"Order lookup failed for #{order_id}",
                    description=message,
                    category="orders",
                    priority="medium",
                    conversation_id=conversation_id,
                    db=db,
                )
                _record_tool("create_support_ticket", ticket, tools_used, tool_results)
                ticket_id = _ticket_code(ticket)
        else:
            kb = handlers.search_knowledge_base(search_query, db=db)
            _record_tool("search_knowledge_base", kb, tools_used, tool_results)
            sources = list(kb.get("results") or [])

    elif intent == "subscription_question":
        sub = handlers.get_subscription()
        _record_tool("get_subscription", sub, tools_used, tool_results)
        kb = handlers.search_knowledge_base(search_query, db=db)
        _record_tool("search_knowledge_base", kb, tools_used, tool_results)
        sources = list(kb.get("results") or [])

    elif intent in {
        "general_question",
        "product_question",
        "billing_question",
        "account_issue",
        "technical_support",
    }:
        kb = handlers.search_knowledge_base(search_query, db=db)
        _record_tool("search_knowledge_base", kb, tools_used, tool_results)
        sources = list(kb.get("results") or [])
        if intent == "general_question" and not sources:
            web = await handlers.search_internet(search_query)
            _record_tool("search_internet", web, tools_used, tool_results)

    elif intent == "complaint":
        escalate_complaints = True
        if db is not None:
            try:
                from app.services.app_settings import get_setting

                escalate_complaints = bool(
                    get_setting(db, "escalate_complaints", True)
                )
            except Exception:  # noqa: BLE001
                escalate_complaints = True
        if escalate_complaints:
            result = handlers.escalate_to_human(
                customer_id=customer_id,
                reason="complaint",
                message=message,
                conversation_id=conversation_id,
                db=db,
            )
            _record_tool("escalate_to_human", result, tools_used, tool_results)
            escalated = True
            ticket_id = _ticket_code(result)
        else:
            kb = handlers.search_knowledge_base(search_query, db=db)
            _record_tool("search_knowledge_base", kb, tools_used, tool_results)
            sources = list(kb.get("results") or [])

    elif intent == "out_of_scope":
        pass

    else:
        kb = handlers.search_knowledge_base(search_query, db=db)
        _record_tool("search_knowledge_base", kb, tools_used, tool_results)
        sources = list(kb.get("results") or [])
        threshold = _confidence_threshold(db)
        if not sources and confidence < threshold and not follow_up:
            result = handlers.escalate_to_human(
                customer_id=customer_id,
                reason="unknown_request",
                message=message,
                conversation_id=conversation_id,
                db=db,
            )
            _record_tool("escalate_to_human", result, tools_used, tool_results)
            escalated = True
            ticket_id = _ticket_code(result)

    context_blocks: list[str] = [
        f"Intent: {intent} ({confidence:.2f})",
    ]
    if follow_up:
        context_blocks.append(
            "This is a FOLLOW-UP to the previous messages. "
            "Answer the new question using that context; do not repeat the full prior answer."
        )
    if tools_used:
        # Compact JSON — less prompt tokens = faster local inference.
        context_blocks.append(
            "Tools: " + json.dumps(tool_results, separators=(",", ":"), default=str)
        )
    if intent == "ticket_status":
        context_blocks.append(
            "Summarize ticket status. If none, offer to create one or escalate."
        )
    elif intent == "general_question" and not sources:
        context_blocks.append(
            "No KB match. Use internet results if present; answer briefly; "
            "then offer help with orders/billing/accounts."
        )
    if escalated:
        context_blocks.append(
            "Escalated to a human."
            + (f" Ticket: {ticket_id}." if ticket_id else "")
        )

    context = "\n".join(context_blocks)
    messages: list[dict[str, str]] = []
    if history:
        # Keep enough turns so follow-ups can see the prior Q&A.
        messages.extend(history[-8:])
    messages.append(
        {
            "role": "user",
            "content": f"Customer: {message}\n{context}\nReply to the customer only.",
        }
    )

    return AgentTurn(
        intent=intent,
        confidence=confidence,
        tools_used=tools_used,
        tool_results=tool_results,
        sources=sources,
        escalated=escalated,
        ticket_id=ticket_id,
        llm_messages=messages,
        is_follow_up=follow_up,
    )


def _try_fast_reply(turn: AgentTurn, *, force: bool = False) -> str | None:
    """Return an instant tool-based reply when the LLM is unnecessary or offline."""
    # Follow-ups need the LLM to use prior chat context (fast path would ignore it).
    if turn.is_follow_up and not force and not turn.escalated:
        if turn.intent != "out_of_scope":
            return None
    return _compose_fast_reply(
        intent=turn.intent,
        tool_results=turn.tool_results,
        escalated=turn.escalated,
        ticket_id=turn.ticket_id,
        force=force,
        allow_kb_fast_path=not turn.is_follow_up,
    )


async def run_support_agent(
    *,
    message: str,
    customer_id: str,
    history: list[dict[str, str]] | None = None,
    db: Session | None = None,
    conversation_id: str | None = None,
) -> AgentResult:
    """Run one agentic turn for a customer support message."""
    from app.services.llm_service import active_model_name

    turn = await prepare_agent_turn(
        message=message,
        customer_id=customer_id,
        history=history,
        db=db,
        conversation_id=conversation_id,
    )

    fast = _try_fast_reply(turn)
    if fast is not None:
        return AgentResult(
            response=fast,
            intent=turn.intent,
            confidence=turn.confidence,
            tools_used=turn.tools_used,
            tool_results=turn.tool_results,
            sources=_source_payload(turn.sources),
            escalated=turn.escalated,
            ticket_id=turn.ticket_id,
            model=active_model_name(),
        )

    system_prompt = _resolve_system_prompt(db)
    try:
        reply = await generate_support_response(
            turn.llm_messages,
            system_prompt=system_prompt,
        )
    except LLMServiceError:
        logger.exception("LLM failed during agent turn; using tool-based fallback")
        reply = _try_fast_reply(turn, force=True) or (
            "I received your request about "
            f"{turn.intent.replace('_', ' ')}, but the AI model is temporarily "
            "unavailable. Please try again in a moment."
        )

    return AgentResult(
        response=reply,
        intent=turn.intent,
        confidence=turn.confidence,
        tools_used=turn.tools_used,
        tool_results=turn.tool_results,
        sources=_source_payload(turn.sources),
        escalated=turn.escalated,
        ticket_id=turn.ticket_id,
        model=active_model_name(),
    )


async def stream_support_agent(
    *,
    message: str,
    customer_id: str,
    history: list[dict[str, str]] | None = None,
    db: Session | None = None,
    conversation_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Stream one agentic turn as status / token / done events."""
    from app.services.llm_service import active_model_name

    turn = await prepare_agent_turn(
        message=message,
        customer_id=customer_id,
        history=history,
        db=db,
        conversation_id=conversation_id,
    )

    yield {
        "type": "status",
        "intent": turn.intent,
        "confidence": turn.confidence,
        "tools_used": turn.tools_used,
        "escalated": turn.escalated,
        "ticket_id": turn.ticket_id,
        "model": active_model_name(),
    }

    fast = _try_fast_reply(turn)
    if fast is not None:
        yield {"type": "token", "content": fast}
        yield {
            "type": "done",
            "response": fast,
            "intent": turn.intent,
            "confidence": turn.confidence,
            "tools_used": turn.tools_used,
            "sources": _source_payload(turn.sources),
            "escalated": turn.escalated,
            "ticket_id": turn.ticket_id,
            "model": active_model_name(),
            "tool_results": turn.tool_results,
        }
        return

    system_prompt = _resolve_system_prompt(db)
    chunks: list[str] = []
    try:
        async for token in stream_support_response(
            turn.llm_messages,
            system_prompt=system_prompt,
        ):
            chunks.append(token)
            yield {"type": "token", "content": token}
    except LLMServiceError:
        logger.exception("LLM stream failed; using tool-based fallback")
        reply = _try_fast_reply(turn, force=True) or (
            "I received your request about "
            f"{turn.intent.replace('_', ' ')}, but the AI model is temporarily "
            "unavailable. Please try again in a moment."
        )
        chunks = [reply]
        yield {"type": "token", "content": reply}

    response = "".join(chunks).strip()
    if not response:
        response = _try_fast_reply(turn, force=True) or (
            "I received your request about "
            f"{turn.intent.replace('_', ' ')}, but the AI model is temporarily "
            "unavailable. Please try again in a moment."
        )

    yield {
        "type": "done",
        "response": response,
        "intent": turn.intent,
        "confidence": turn.confidence,
        "tools_used": turn.tools_used,
        "sources": _source_payload(turn.sources),
        "escalated": turn.escalated,
        "ticket_id": turn.ticket_id,
        "model": active_model_name(),
        "tool_results": turn.tool_results,
    }


def _compose_fast_reply(
    *,
    intent: str,
    tool_results: list[dict[str, Any]],
    escalated: bool,
    ticket_id: str | None,
    force: bool = False,
    allow_kb_fast_path: bool = True,
) -> str | None:
    """Build an instant reply from tools when the LLM is unnecessary or offline.

    When force=True (LLM failure), always return a best-effort string.
    Otherwise return None so the LLM can phrase open-ended answers.
    """
    if intent == "out_of_scope":
        return (
            "I'm a customer support assistant for product, order, billing, and "
            "account questions. I can't help with that topic — please ask about "
            "an order, subscription, account, or technical issue."
        )
    if escalated:
        suffix = f" Your ticket ID is {ticket_id}." if ticket_id else ""
        return (
            "I've connected you with a human support agent who will follow up shortly."
            + suffix
        )

    for item in tool_results:
        if item["tool"] == "get_ticket_status":
            result = item["result"]
            if result.get("ok") and result.get("ticket"):
                ticket = result["ticket"]
                return (
                    f"Ticket {ticket['ticket_id']} ({ticket['title']}) is "
                    f"{ticket['status'].replace('_', ' ')}. "
                    f"Priority: {ticket['priority']}. "
                    f"Assigned to: {ticket.get('assigned_to', 'Unassigned')}."
                )
            if result.get("ok"):
                tickets = result.get("tickets") or []
                if not tickets:
                    return (
                        "You don't have any support tickets yet. "
                        "I can create one or connect you with a human agent."
                    )
                lines = [
                    f"- {t['ticket_id']}: {t['title']} ({t['status'].replace('_', ' ')})"
                    for t in tickets
                ]
                return "Here are your recent tickets:\n" + "\n".join(lines)
            return str(result.get("error") or "I could not look up that ticket.")

        if item["tool"] == "get_order_status":
            # Follow-ups about an order still need the LLM when not forced.
            if not force and not allow_kb_fast_path:
                continue
            result = item["result"]
            if result.get("ok"):
                order = result["order"]
                return (
                    f"Order #{order['order_id']} is currently {order['status']}. "
                    f"Estimated delivery: {order['estimated_delivery']}. "
                    f"Tracking: {order.get('tracking_number', 'n/a')}."
                )
            return str(result.get("error") or "I could not find that order.")

        if item["tool"] == "get_subscription" and item["result"].get("ok"):
            # Subscription + KB: let LLM merge unless we're forced offline.
            if not force and any(
                t["tool"] == "search_knowledge_base" for t in tool_results
            ):
                continue
            sub = item["result"]["subscription"]
            return (
                f"Your subscription plan is {sub['plan']} ({sub['status']}). "
                f"Renewal date: {sub['renewal_date']}."
            )

        if item["tool"] == "search_knowledge_base":
            results = item["result"].get("results") or []
            if results:
                top = results[0]
                similarity = float(top.get("similarity") or 0)
                # Strong KB hit → skip slow LLM; good enough for support FAQs.
                # Follow-ups disable this so the model can answer the new question.
                if force or (allow_kb_fast_path and similarity >= 0.25):
                    return f"Based on our {top['title']} guide: {top['content']}"

        if force and item["tool"] == "search_internet":
            result = item["result"]
            if result.get("ok"):
                results = result.get("results") or []
                if results:
                    top = results[0]
                    return (
                        f"{top.get('title')}: {top.get('snippet')} "
                        f"(source: {top.get('source', 'internet')})"
                    )

    return None if not force else (
        "I received your request about "
        f"{intent.replace('_', ' ')}, but the AI model is temporarily unavailable. "
        "Please try again in a moment."
    )


# Backward-compatible alias used by older tests/imports.
def _fallback_reply(
    *,
    intent: str,
    tool_results: list[dict[str, Any]],
    escalated: bool,
    ticket_id: str | None,
) -> str:
    return _compose_fast_reply(
        intent=intent,
        tool_results=tool_results,
        escalated=escalated,
        ticket_id=ticket_id,
        force=True,
    ) or (
        "I received your request about "
        f"{intent.replace('_', ' ')}, but the AI model is temporarily unavailable. "
        "Please try again in a moment."
    )
