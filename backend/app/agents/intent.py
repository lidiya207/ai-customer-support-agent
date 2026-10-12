"""Lightweight intent detection for the support agent."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class IntentResult:
    intent: str
    confidence: float
    order_id: str | None = None
    ticket_code: str | None = None
    is_follow_up: bool = False


_ORDER_RE = re.compile(r"(?:order\s*#?\s*|#)(\d{4,})", re.IGNORECASE)
_BARE_ORDER_RE = re.compile(r"\b(\d{5})\b")
_TICKET_RE = re.compile(r"\b(TCK-[A-Z0-9]{6,})\b", re.IGNORECASE)

# Short replies that usually refer to the previous assistant answer.
_FOLLOW_UP_RE = re.compile(
    r"\b("
    r"it|that|this|they|them|those|these|"
    r"the link|the order|the ticket|the email|the package|the plan|"
    r"tell me more|more details|explain(?:\s+more)?|clarify|"
    r"what about|how long|how soon|when (?:will|does|is)|"
    r"why|and then|what if|how about|does that|is that|"
    r"can you (?:also|explain|clarify)|same (?:order|ticket)|"
    r"still waiting|any update|what next|next step"
    r")\b",
    re.IGNORECASE,
)

# Only clearly inappropriate / unrelated-to-business topics.
_OUT_OF_SCOPE_PATTERNS = (
    "jesus",
    "bible",
    "quran",
    "allah",
    "church",
    "mosque",
    "religion",
    "pray for",
    "politics",
    "election",
    "president",
    "democrat",
    "republican",
    "medical advice",
    "diagnose me",
    "prescription",
    "how to make a bomb",
    "hack into",
)


def extract_order_id(text: str) -> str | None:
    match = _ORDER_RE.search(text)
    if match:
        return match.group(1)
    match = _BARE_ORDER_RE.search(text)
    if match:
        return match.group(1)
    return None


def extract_ticket_code(text: str) -> str | None:
    match = _TICKET_RE.search(text)
    if match:
        return match.group(1).upper()
    return None


def is_follow_up(message: str, history: list[dict[str, str]] | None) -> bool:
    """True when the message likely depends on the previous turn."""
    if not history:
        return False
    text = message.strip()
    if not text:
        return False
    lower = text.lower()
    if _FOLLOW_UP_RE.search(lower):
        return True
    words = lower.split()
    # Short clarifying questions in an ongoing chat ("30 minutes?", "and then?", "so?")
    if len(words) <= 6 and (
        "?" in text
        or lower.startswith(("and ", "also ", "so ", "but ", "ok ", "okay "))
    ):
        return True
    return False


def last_user_message(history: list[dict[str, str]] | None) -> str | None:
    if not history:
        return None
    for item in reversed(history):
        if item.get("role") == "user" and (item.get("content") or "").strip():
            return item["content"].strip()
    return None


def ids_from_history(
    history: list[dict[str, str]] | None,
) -> tuple[str | None, str | None]:
    """Pull the most recent order / ticket id mentioned in prior turns."""
    if not history:
        return None, None
    order_id: str | None = None
    ticket_code: str | None = None
    for item in reversed(history):
        content = item.get("content") or ""
        if order_id is None:
            order_id = extract_order_id(content)
        if ticket_code is None:
            ticket_code = extract_ticket_code(content)
        if order_id and ticket_code:
            break
    return order_id, ticket_code


def detect_intent(
    message: str,
    history: list[dict[str, str]] | None = None,
) -> IntentResult:
    text = message.lower().strip()
    order_id = extract_order_id(message)
    ticket_code = extract_ticket_code(message)
    follow_up = is_follow_up(message, history)

    # Carry ids from prior turns when the customer refers to "my order" / "that ticket".
    if history and (follow_up or not order_id or not ticket_code):
        hist_order, hist_ticket = ids_from_history(history)
        if not order_id:
            order_id = hist_order
        if not ticket_code:
            ticket_code = hist_ticket

    if any(pattern in text for pattern in _OUT_OF_SCOPE_PATTERNS):
        return IntentResult(intent="out_of_scope", confidence=0.95, is_follow_up=follow_up)

    rules: list[tuple[str, float, tuple[str, ...]]] = [
        (
            "human_support_request",
            0.95,
            (
                "talk to a human",
                "speak to a human",
                "human agent",
                "real person",
                "customer service agent",
                "talk to someone",
                "speak to an agent",
                "human support",
            ),
        ),
        (
            "refund_request",
            0.9,
            ("refund", "charged twice", "money back", "double charged"),
        ),
        (
            "ticket_status",
            0.92,
            (
                "ticket status",
                "my ticket",
                "check ticket",
                "ticket update",
                "support ticket",
                "status of my ticket",
                "where is my ticket",
            ),
        ),
        (
            "order_status",
            0.9,
            (
                "where is my order",
                "track my order",
                "order status",
                "package",
                "shipment",
                "delivery",
                "hasn't arrived",
                "hasnt arrived",
            ),
        ),
        (
            "subscription_question",
            0.85,
            ("subscription", "renewal", "cancel plan", "upgrade plan", "downgrade"),
        ),
        (
            "billing_question",
            0.8,
            ("billing", "invoice", "payment", "charged", "price"),
        ),
        (
            "account_issue",
            0.85,
            ("password", "reset password", "login", "can't sign in", "account locked"),
        ),
        (
            "technical_support",
            0.8,
            ("wifi", "wi-fi", "troubleshoot", "not working", "error", "bug"),
        ),
        (
            "complaint",
            0.85,
            ("complaint", "angry", "frustrated", "terrible", "worst"),
        ),
    ]

    for intent, confidence, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return IntentResult(
                intent=intent,
                confidence=confidence,
                order_id=order_id,
                ticket_code=ticket_code,
                is_follow_up=follow_up,
            )

    if ticket_code:
        return IntentResult(
            intent="ticket_status",
            confidence=0.9,
            order_id=order_id,
            ticket_code=ticket_code,
            is_follow_up=follow_up,
        )

    # Follow-up about delivery / tracking with a known order id from history.
    if follow_up and order_id and any(
        word in text
        for word in (
            "arrive",
            "arrival",
            "delivery",
            "deliver",
            "tracking",
            "shipped",
            "package",
            "when",
            "where",
            "status",
        )
    ):
        return IntentResult(
            intent="order_status",
            confidence=0.85,
            order_id=order_id,
            ticket_code=ticket_code,
            is_follow_up=True,
        )

    if order_id and any(
        word in text
        for word in ("order", "package", "shipment", "delivery", "track", "where")
    ):
        return IntentResult(
            intent="order_status",
            confidence=0.8,
            order_id=order_id,
            ticket_code=ticket_code,
            is_follow_up=follow_up,
        )

    if order_id and not follow_up:
        return IntentResult(
            intent="order_status",
            confidence=0.8,
            order_id=order_id,
            is_follow_up=False,
        )

    if any(
        word in text
        for word in ("policy", "how do i", "what is", "what's", "hours", "shipping", "explain")
    ):
        return IntentResult(
            intent="general_question",
            confidence=0.7,
            order_id=order_id,
            ticket_code=ticket_code,
            is_follow_up=follow_up,
        )

    # Default: treat as a normal general question (search KB, answer helpfully).
    return IntentResult(
        intent="general_question",
        confidence=0.55,
        order_id=order_id,
        ticket_code=ticket_code,
        is_follow_up=follow_up,
    )
