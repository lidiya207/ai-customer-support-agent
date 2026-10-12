from unittest.mock import AsyncMock, patch

import pytest

from app.agents.intent import detect_intent, extract_order_id, extract_ticket_code
from app.agents.orchestrator import run_support_agent
from app.rag.knowledge import search_knowledge
from app.tools import store
from app.tools.handlers import get_order_status


@pytest.fixture(autouse=True)
def _clear_stores() -> None:
    store.reset_stores()


def test_extract_order_id() -> None:
    assert extract_order_id("Where is order #45231?") == "45231"
    assert extract_order_id("track 45321 please") == "45321"


def test_detect_order_intent() -> None:
    result = detect_intent("Where is my order #45231?")
    assert result.intent == "order_status"
    assert result.order_id == "45231"


def test_detect_human_request() -> None:
    result = detect_intent("I want to talk to a human please")
    assert result.intent == "human_support_request"


def test_detect_refund() -> None:
    result = detect_intent("I was charged twice and need a refund")
    assert result.intent == "refund_request"


def test_detect_ticket_status() -> None:
    result = detect_intent("Can you check my ticket status?")
    assert result.intent == "ticket_status"


def test_extract_ticket_code() -> None:
    assert extract_ticket_code("What about TCK-AB12CD34?") == "TCK-AB12CD34"
    result = detect_intent("Status of TCK-ZZ99YY88 please")
    assert result.intent == "ticket_status"
    assert result.ticket_code == "TCK-ZZ99YY88"


def test_detect_out_of_scope() -> None:
    result = detect_intent("Tell me about Jesus")
    assert result.intent == "out_of_scope"


def test_detect_general_tech_question() -> None:
    result = detect_intent("what is full stack")
    assert result.intent == "general_question"


def test_knowledge_search_finds_password_doc() -> None:
    results = search_knowledge("How do I reset my password?")
    assert results
    assert any("password" in r["title"].lower() for r in results)


def test_vector_embedding_similarity_ranks_related_text() -> None:
    from app.rag.embeddings import cosine_similarity, embed_text

    query = embed_text("reset my password link")
    password = embed_text("Forgot Password reset link email")
    shipping = embed_text("express shipping delivery tracking")
    assert cosine_similarity(query, password) > cosine_similarity(query, shipping)


def test_get_order_status_tool() -> None:
    result = get_order_status("45231")
    assert result["ok"] is True
    assert result["order"]["status"] == "shipped"


@pytest.mark.asyncio
async def test_agent_order_lookup_uses_tool() -> None:
    with patch(
        "app.agents.orchestrator.generate_support_response",
        new_callable=AsyncMock,
        return_value="Your order 45231 has shipped.",
    ):
        result = await run_support_agent(
            message="Where is order #45231?",
            customer_id="user-1",
        )

    assert result.intent == "order_status"
    assert "get_order_status" in result.tools_used
    assert result.escalated is False
    assert "shipped" in result.response.lower() or "45231" in result.response


@pytest.mark.asyncio
async def test_agent_escalates_human_request() -> None:
    with patch(
        "app.agents.orchestrator.generate_support_response",
        new_callable=AsyncMock,
        return_value="A human agent will contact you shortly.",
    ):
        result = await run_support_agent(
            message="Please let me speak to an agent",
            customer_id="user-1",
        )

    assert result.intent == "human_support_request"
    assert result.escalated is True
    assert result.ticket_id is not None
    assert "escalate_to_human" in result.tools_used


@pytest.mark.asyncio
async def test_agent_general_question_uses_internet() -> None:
    with (
        patch(
            "app.agents.orchestrator.generate_support_response",
            new_callable=AsyncMock,
            return_value="Full stack means frontend and backend development.",
        ),
        patch(
            "app.tools.handlers.search_internet",
            new_callable=AsyncMock,
            return_value={
                "ok": True,
                "query": "what is full stack",
                "count": 1,
                "results": [
                    {
                        "title": "Full stack",
                        "snippet": "Frontend and backend development.",
                        "url": "https://example.com",
                        "source": "wikipedia",
                    }
                ],
            },
        ),
    ):
        result = await run_support_agent(
            message="what is full stack",
            customer_id="user-1",
        )

    assert result.intent == "general_question"
    assert "search_internet" in result.tools_used
    assert result.escalated is False


@pytest.mark.asyncio
async def test_agent_out_of_scope_does_not_escalate() -> None:
    with patch(
        "app.agents.orchestrator.generate_support_response",
        new_callable=AsyncMock,
        return_value="I only help with customer support questions.",
    ):
        result = await run_support_agent(
            message="Tell me about Jesus",
            customer_id="user-1",
        )

    assert result.intent == "out_of_scope"
    assert result.escalated is False
    assert "escalate_to_human" not in result.tools_used


@pytest.mark.asyncio
async def test_agent_fallback_without_llm() -> None:
    from app.services.llm_service import LLMServiceError

    with patch(
        "app.agents.orchestrator.generate_support_response",
        new_callable=AsyncMock,
        side_effect=LLMServiceError("offline"),
    ):
        result = await run_support_agent(
            message="Where is order #45231?",
            customer_id="user-1",
        )

    assert "get_order_status" in result.tools_used
    assert "45231" in result.response or "shipped" in result.response.lower()


def test_follow_up_detection() -> None:
    from app.agents.intent import is_follow_up

    history = [
        {"role": "user", "content": "How do I reset my password?"},
        {"role": "assistant", "content": "Click Forgot Password on the login page."},
    ]
    assert is_follow_up("How long is the link valid?", history) is True
    assert is_follow_up("How do I reset my password?", None) is False


@pytest.mark.asyncio
async def test_follow_up_uses_history_and_skips_kb_fast_path() -> None:
    history = [
        {"role": "user", "content": "How do I reset my password?"},
        {
            "role": "assistant",
            "content": "Click Forgot Password. The reset link is valid for 30 minutes.",
        },
    ]
    with patch(
        "app.agents.orchestrator.generate_support_response",
        new_callable=AsyncMock,
        return_value="The reset link is valid for 30 minutes.",
    ) as mock_llm:
        result = await run_support_agent(
            message="How long is the link valid?",
            customer_id="user-1",
            history=history,
        )

    assert mock_llm.await_count == 1
    sent = mock_llm.await_args.args[0]
    assert any("reset my password" in m["content"].lower() for m in sent)
    assert "30 minutes" in result.response.lower()


@pytest.mark.asyncio
async def test_follow_up_reuses_order_id_from_history() -> None:
    history = [
        {"role": "user", "content": "Where is my order #45231?"},
        {"role": "assistant", "content": "Order #45231 is currently shipped."},
    ]
    with patch(
        "app.agents.orchestrator.generate_support_response",
        new_callable=AsyncMock,
        return_value="It should arrive by the estimated delivery date on the order.",
    ):
        result = await run_support_agent(
            message="When will it arrive?",
            customer_id="user-1",
            history=history,
        )

    assert result.intent == "order_status"
    assert "get_order_status" in result.tools_used
