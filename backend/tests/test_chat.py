from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.agents.orchestrator import AgentResult
from app.services.llm_service import LLMServiceError


def test_chat_requires_auth(client: TestClient) -> None:
    response = client.post("/api/chat", json={"message": "Hello"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."


def test_chat_success(client: TestClient, customer_headers: dict) -> None:
    agent_result = AgentResult(
        response="To reset your password, use the Forgot Password link.",
        intent="account_issue",
        confidence=0.85,
        tools_used=["search_knowledge_base"],
        sources=[{"document_id": "kb-password-reset", "title": "Password Reset", "similarity": 0.5}],
        escalated=False,
        ticket_id=None,
        model="llama3.2",
    )
    with patch(
        "app.api.chat.run_support_agent",
        new_callable=AsyncMock,
        return_value=agent_result,
    ) as mock_agent:
        response = client.post(
            "/api/chat",
            json={"message": "How do I reset my password?"},
            headers=customer_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "To reset your password, use the Forgot Password link."
    assert data["intent"] == "account_issue"
    assert data["tools_used"] == ["search_knowledge_base"]
    assert data["escalated"] is False
    assert data["conversation_id"]
    assert "model" in data
    mock_agent.assert_awaited_once()


def test_chat_rejects_empty_message(client: TestClient, customer_headers: dict) -> None:
    response = client.post(
        "/api/chat",
        json={"message": ""},
        headers=customer_headers,
    )
    assert response.status_code == 422


def test_chat_agent_failure(client: TestClient, customer_headers: dict) -> None:
    with patch(
        "app.api.chat.run_support_agent",
        new_callable=AsyncMock,
        side_effect=LLMServiceError("Unable to reach the AI service. Is Ollama running?"),
    ):
        response = client.post(
            "/api/chat",
            json={"message": "Hello"},
            headers=customer_headers,
        )

    assert response.status_code == 503
    assert "Unable to reach" in response.json()["detail"]


def test_chat_stream_success(client: TestClient, customer_headers: dict) -> None:
    async def fake_stream(**_kwargs):
        yield {
            "type": "status",
            "intent": "account_issue",
            "confidence": 0.85,
            "tools_used": ["search_knowledge_base"],
            "escalated": False,
            "ticket_id": None,
            "model": "llama3.2",
        }
        yield {"type": "token", "content": "Reset "}
        yield {"type": "token", "content": "via Forgot Password."}
        yield {
            "type": "done",
            "response": "Reset via Forgot Password.",
            "intent": "account_issue",
            "confidence": 0.85,
            "tools_used": ["search_knowledge_base"],
            "sources": [],
            "escalated": False,
            "ticket_id": None,
            "model": "llama3.2",
            "tool_results": [],
        }

    with patch("app.api.chat.stream_support_agent", side_effect=fake_stream):
        response = client.post(
            "/api/chat/stream",
            json={"message": "How do I reset my password?"},
            headers=customer_headers,
        )

    assert response.status_code == 200
    body = response.text
    assert "event: meta" in body
    assert "event: status" in body
    assert "event: token" in body
    assert "event: done" in body
    assert "Forgot Password" in body


def test_ai_status_online(client: TestClient) -> None:
    with patch(
        "app.api.ai.check_ollama_status",
        new_callable=AsyncMock,
        return_value={
            "status": "online",
            "provider": "ollama",
            "model": "llama3.2",
        },
    ):
        response = client.get("/api/ai/status")

    assert response.status_code == 200
    assert response.json() == {
        "status": "online",
        "provider": "ollama",
        "model": "llama3.2",
    }


def test_ai_status_offline(client: TestClient) -> None:
    with patch(
        "app.api.ai.check_ollama_status",
        new_callable=AsyncMock,
        return_value={"status": "offline", "provider": "ollama"},
    ):
        response = client.get("/api/ai/status")

    assert response.status_code == 200
    assert response.json() == {"status": "offline", "provider": "ollama"}
