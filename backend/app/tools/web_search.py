"""Internet search tool for the support agent (DuckDuckGo + Wikipedia)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def _fetch_duckduckgo(
    client: httpx.AsyncClient, query: str, limit: int
) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    ddg = await client.get(
        "https://api.duckduckgo.com/",
        params={
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        },
        headers={"User-Agent": "AI-Customer-Support-Agent/1.0"},
    )
    if ddg.status_code >= 400:
        return results

    data = ddg.json()
    abstract = str(data.get("AbstractText") or "").strip()
    heading = str(data.get("Heading") or "").strip()
    abstract_url = str(data.get("AbstractURL") or "").strip()
    if abstract:
        results.append(
            {
                "title": heading or "Summary",
                "snippet": abstract[:500],
                "url": abstract_url,
                "source": "duckduckgo",
            }
        )
    for topic in (data.get("RelatedTopics") or [])[:limit]:
        if not isinstance(topic, dict):
            continue
        text = str(topic.get("Text") or "").strip()
        url = ""
        first_url = topic.get("FirstURL")
        if isinstance(first_url, str):
            url = first_url
        if text:
            results.append(
                {
                    "title": text.split(" - ")[0][:80],
                    "snippet": text[:300],
                    "url": url,
                    "source": "duckduckgo",
                }
            )
    return results


async def _fetch_wikipedia(
    client: httpx.AsyncClient, query: str
) -> list[dict[str, str]]:
    wiki = await client.get(
        "https://en.wikipedia.org/api/rest_v1/page/summary/"
        + quote_plus(query.replace(" ", "_")),
        headers={"User-Agent": "AI-Customer-Support-Agent/1.0"},
    )
    if wiki.status_code != 200:
        return []

    wiki_data = wiki.json()
    extract = str(wiki_data.get("extract") or "").strip()
    title = str(wiki_data.get("title") or query).strip()
    page_url = ""
    urls = wiki_data.get("content_urls") or {}
    if isinstance(urls, dict):
        desktop = urls.get("desktop") or {}
        if isinstance(desktop, dict):
            page_url = str(desktop.get("page") or "")
    if not extract:
        return []
    return [
        {
            "title": title,
            "snippet": extract[:500],
            "url": page_url,
            "source": "wikipedia",
        }
    ]


async def search_web(query: str, *, limit: int = 3) -> dict[str, Any]:
    """Search the public web for a short answer and related links."""
    settings = get_settings()
    if not settings.ENABLE_WEB_SEARCH:
        return {"ok": False, "error": "Web search is disabled."}

    cleaned = query.strip()
    if not cleaned:
        return {"ok": False, "error": "Empty search query."}

    timeout = httpx.Timeout(settings.WEB_SEARCH_TIMEOUT_SECONDS, connect=5.0)
    results: list[dict[str, str]] = []

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            ddg_task = _fetch_duckduckgo(client, cleaned, limit)
            wiki_task = _fetch_wikipedia(client, cleaned)
            ddg_results, wiki_results = await asyncio.gather(
                ddg_task, wiki_task, return_exceptions=True
            )
            if isinstance(ddg_results, list):
                results.extend(ddg_results)
            elif isinstance(ddg_results, BaseException):
                logger.warning("DuckDuckGo search failed: %s", ddg_results)
            if isinstance(wiki_results, list):
                results.extend(wiki_results)
            elif isinstance(wiki_results, BaseException):
                logger.warning("Wikipedia search failed: %s", wiki_results)
    except httpx.HTTPError as exc:
        logger.warning("Web search failed: %s", exc)
        return {"ok": False, "error": "Unable to reach the internet search service."}

    # Deduplicate by snippet prefix.
    unique: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in results:
        key = item.get("snippet", "")[:80].lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
        if len(unique) >= limit:
            break

    if not unique:
        return {
            "ok": False,
            "error": "No useful internet results found.",
            "query": cleaned,
        }

    return {
        "ok": True,
        "query": cleaned,
        "count": len(unique),
        "results": unique,
    }
