"""In-memory stores for simulated orders and created tickets (MVP)."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any


_lock = threading.Lock()

# Simulated order catalog the agent can look up.
ORDERS: dict[str, dict[str, Any]] = {
    "45231": {
        "order_id": "45231",
        "status": "shipped",
        "estimated_delivery": "October 9",
        "carrier": "Express Mail",
        "tracking_number": "TRK-88421",
        "items": ["Wireless Headphones"],
    },
    "45321": {
        "order_id": "45321",
        "status": "delayed",
        "estimated_delivery": "October 5 (missed)",
        "carrier": "Standard Shipping",
        "tracking_number": "TRK-99102",
        "items": ["USB-C Hub"],
    },
    "10001": {
        "order_id": "10001",
        "status": "delivered",
        "estimated_delivery": "September 28",
        "carrier": "Standard Shipping",
        "tracking_number": "TRK-11001",
        "items": ["Pro Subscription Card"],
    },
}

SUBSCRIPTIONS: dict[str, dict[str, Any]] = {
    "default": {
        "plan": "Pro",
        "status": "active",
        "renewal_date": "November 1",
        "amount": "$29/month",
    }
}

_tickets: list[dict[str, Any]] = []
_escalations: list[dict[str, Any]] = []


def get_order(order_id: str) -> dict[str, Any] | None:
    cleaned = order_id.strip().lstrip("#")
    return ORDERS.get(cleaned)


def get_subscription(customer_key: str = "default") -> dict[str, Any]:
    return SUBSCRIPTIONS.get(customer_key, SUBSCRIPTIONS["default"])


def create_ticket(
    *,
    customer_id: str,
    title: str,
    description: str,
    category: str = "general",
    priority: str = "medium",
    conversation_id: str | None = None,
) -> dict[str, Any]:
    ticket = {
        "ticket_id": f"TCK-{uuid.uuid4().hex[:8].upper()}",
        "customer_id": customer_id,
        "conversation_id": conversation_id,
        "title": title,
        "description": description,
        "priority": priority,
        "category": category,
        "status": "open",
        "assigned_agent": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        _tickets.append(ticket)
    return ticket


def escalate_conversation(
    *,
    customer_id: str,
    reason: str,
    message: str,
    ticket_id: str | None = None,
) -> dict[str, Any]:
    record = {
        "escalation_id": f"ESC-{uuid.uuid4().hex[:8].upper()}",
        "customer_id": customer_id,
        "reason": reason,
        "message": message,
        "ticket_id": ticket_id,
        "status": "escalated",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        _escalations.append(record)
    return record


def list_tickets() -> list[dict[str, Any]]:
    with _lock:
        return list(_tickets)


def reset_stores() -> None:
    """Clear mutable stores — used by tests."""
    with _lock:
        _tickets.clear()
        _escalations.clear()
