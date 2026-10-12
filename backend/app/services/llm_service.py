"""LLM service layer — Ollama (local) and OpenAI (internet) providers."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a professional AI customer support assistant.\n\n"
    "Answer customers clearly and concisely.\n\n"
    "If you do not know an answer, say that you do not know.\n\n"
    "Do not invent company policies, prices, order information, or customer information.\n\n"
    "When tool results or knowledge excerpts are provided, use them to answer."
)


class LLMServiceError(Exception):
    """Raised when the LLM provider fails to generate a response."""

    def __init__(self, message: str, *, status_code: int = 503) -> None:
        super().__init__(message)
        self.status_code = status_code


def _build_messages(
    messages: list[dict[str, str]],
    *,
    system_prompt: str | None = None,
) -> list[dict[str, str]]:
    prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT
    return [{"role": "system", "content": prompt}, *messages]


def resolve_provider() -> str:
    settings = get_settings()
    provider = (settings.LLM_PROVIDER or "auto").strip().lower()
    if provider == "auto":
        return "openai" if settings.OPENAI_API_KEY.strip() else "ollama"
    if provider in {"openai", "ollama"}:
        return provider
    return "ollama"


def active_model_name() -> str:
    settings = get_settings()
    if resolve_provider() == "openai":
        return settings.OPENAI_MODEL
    return settings.OLLAMA_MODEL


def _ollama_timeout() -> httpx.Timeout:
    settings = get_settings()
    return httpx.Timeout(settings.OLLAMA_TIMEOUT_SECONDS, connect=10.0)


def _ollama_options() -> dict[str, Any]:
    settings = get_settings()
    return {
        "num_predict": settings.OLLAMA_NUM_PREDICT,
        "num_ctx": settings.OLLAMA_NUM_CTX,
        "temperature": 0.3,
    }


def _ollama_chat_payload(
    messages: list[dict[str, str]],
    *,
    system_prompt: str | None,
    stream: bool,
) -> dict[str, Any]:
    settings = get_settings()
    return {
        "model": settings.OLLAMA_MODEL,
        "messages": _build_messages(messages, system_prompt=system_prompt),
        "stream": stream,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        "options": _ollama_options(),
    }


async def _generate_ollama(
    messages: list[dict[str, str]],
    *,
    system_prompt: str | None,
) -> str:
    settings = get_settings()
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = _ollama_chat_payload(
        messages, system_prompt=system_prompt, stream=False
    )

    try:
        async with httpx.AsyncClient(timeout=_ollama_timeout()) as client:
            response = await client.post(url, json=payload)
    except httpx.ConnectError as exc:
        logger.error("Ollama connection failed: %s", exc)
        raise LLMServiceError(
            "Unable to reach the AI service. Is Ollama running?"
        ) from exc
    except httpx.TimeoutException as exc:
        logger.error("Ollama request timed out: %s", exc)
        raise LLMServiceError(
            "The AI service timed out. Please try again in a moment — "
            "the local model can be slow on first reply."
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("Ollama HTTP error: %s", exc)
        raise LLMServiceError("Unexpected error talking to the AI service.") from exc

    if response.status_code == 404:
        raise LLMServiceError(
            f"Model '{settings.OLLAMA_MODEL}' is not installed in Ollama.",
            status_code=502,
        )
    if response.status_code >= 400:
        raise LLMServiceError("The AI service returned an error.", status_code=502)

    try:
        data = response.json()
    except ValueError as exc:
        raise LLMServiceError("Invalid response from the AI service.") from exc

    message = data.get("message") if isinstance(data, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise LLMServiceError("Invalid response from the AI service.")
    return content.strip()


async def _generate_openai(
    messages: list[dict[str, str]],
    *,
    system_prompt: str | None,
) -> str:
    settings = get_settings()
    if not settings.OPENAI_API_KEY.strip():
        raise LLMServiceError(
            "OPENAI_API_KEY is not set. Add it to backend/.env to use internet AI."
        )

    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": _build_messages(messages, system_prompt=system_prompt),
        "temperature": 0.4,
        "max_tokens": settings.OLLAMA_NUM_PREDICT,
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY.strip()}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.HTTPError as exc:
        logger.error("OpenAI request failed: %s", exc)
        raise LLMServiceError("Unable to reach OpenAI over the internet.") from exc

    if response.status_code >= 400:
        logger.error("OpenAI returned %s: %s", response.status_code, response.text)
        raise LLMServiceError("OpenAI returned an error.", status_code=502)

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMServiceError("Invalid response from OpenAI.") from exc

    if not isinstance(content, str) or not content.strip():
        raise LLMServiceError("Invalid response from OpenAI.")
    return content.strip()


async def generate_support_response(
    messages: list[dict[str, str]],
    *,
    system_prompt: str | None = None,
) -> str:
    """Generate a reply via OpenAI (internet) or Ollama (local)."""
    provider = resolve_provider()
    if provider == "openai":
        return await _generate_openai(messages, system_prompt=system_prompt)
    return await _generate_ollama(messages, system_prompt=system_prompt)


async def _stream_ollama(
    messages: list[dict[str, str]],
    *,
    system_prompt: str | None,
) -> AsyncIterator[str]:
    settings = get_settings()
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = _ollama_chat_payload(
        messages, system_prompt=system_prompt, stream=True
    )

    try:
        async with httpx.AsyncClient(timeout=_ollama_timeout()) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code == 404:
                    raise LLMServiceError(
                        f"Model '{settings.OLLAMA_MODEL}' is not installed in Ollama.",
                        status_code=502,
                    )
                if response.status_code >= 400:
                    raise LLMServiceError(
                        "The AI service returned an error.", status_code=502
                    )
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except ValueError:
                        continue
                    message = data.get("message") if isinstance(data, dict) else None
                    content = message.get("content") if isinstance(message, dict) else None
                    if isinstance(content, str) and content:
                        yield content
    except LLMServiceError:
        raise
    except httpx.ConnectError as exc:
        raise LLMServiceError(
            "Unable to reach the AI service. Is Ollama running?"
        ) from exc
    except httpx.TimeoutException as exc:
        raise LLMServiceError(
            "The AI service timed out. Please try again in a moment — "
            "the local model can be slow on first reply."
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("Ollama stream HTTP error: %s", exc)
        raise LLMServiceError("Unexpected error talking to the AI service.") from exc


async def _stream_openai(
    messages: list[dict[str, str]],
    *,
    system_prompt: str | None,
) -> AsyncIterator[str]:
    settings = get_settings()
    if not settings.OPENAI_API_KEY.strip():
        raise LLMServiceError(
            "OPENAI_API_KEY is not set. Add it to backend/.env to use internet AI."
        )

    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": _build_messages(messages, system_prompt=system_prompt),
        "temperature": 0.4,
        "max_tokens": settings.OLLAMA_NUM_PREDICT,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY.strip()}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    logger.error(
                        "OpenAI stream returned %s: %s",
                        response.status_code,
                        body[:500],
                    )
                    raise LLMServiceError("OpenAI returned an error.", status_code=502)
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta") or {}
                        content = delta.get("content")
                    except (ValueError, KeyError, IndexError, TypeError):
                        continue
                    if isinstance(content, str) and content:
                        yield content
    except LLMServiceError:
        raise
    except httpx.HTTPError as exc:
        logger.error("OpenAI stream failed: %s", exc)
        raise LLMServiceError("Unable to reach OpenAI over the internet.") from exc


async def stream_support_response(
    messages: list[dict[str, str]],
    *,
    system_prompt: str | None = None,
) -> AsyncIterator[str]:
    """Stream reply tokens via OpenAI or Ollama."""
    provider = resolve_provider()
    if provider == "openai":
        async for token in _stream_openai(messages, system_prompt=system_prompt):
            yield token
    else:
        async for token in _stream_ollama(messages, system_prompt=system_prompt):
            yield token


async def check_ollama_status() -> dict[str, str]:
    """Return AI status for the active provider."""
    settings = get_settings()
    provider = resolve_provider()

    if provider == "openai":
        if not settings.OPENAI_API_KEY.strip():
            return {"status": "offline", "provider": "openai"}
        return {
            "status": "online",
            "provider": "openai",
            "model": settings.OPENAI_MODEL,
        }

    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=2.0)) as client:
            response = await client.get(url)
            response.raise_for_status()
    except (httpx.HTTPError, ValueError):
        logger.warning("Ollama status check failed — reporting offline")
        return {"status": "offline", "provider": "ollama"}

    return {
        "status": "online",
        "provider": "ollama",
        "model": settings.OLLAMA_MODEL,
    }


async def warm_ollama_model() -> bool:
    """Load the Ollama model into memory so the first chat reply is faster."""
    if resolve_provider() != "ollama":
        return False

    settings = get_settings()
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [{"role": "user", "content": "OK"}],
        "stream": False,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        "options": {"num_predict": 1, "temperature": 0},
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0)) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        logger.info("Warmed Ollama model '%s'", settings.OLLAMA_MODEL)
        return True
    except httpx.HTTPError as exc:
        logger.warning("Could not warm Ollama model: %s", exc)
        return False
