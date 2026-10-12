"""Knowledge base: seeded docs + DB chunks with vector similarity search."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.knowledge import (
    DocumentStatus,
    DocumentType,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.rag.embeddings import (
    cosine_similarity,
    embed_text,
    embedding_from_json,
    embedding_to_json,
)


@dataclass(frozen=True)
class SeedDocument:
    id: str
    title: str
    category: str
    content: str


SEED_DOCUMENTS: list[SeedDocument] = [
    SeedDocument(
        id="kb-password-reset",
        title="Password Reset",
        category="account",
        content=(
            "To reset your password, open the login page and click Forgot Password. "
            "Enter the email on your account. You will receive a reset link valid for "
            "30 minutes. If you do not see the email, check spam or request a new link."
        ),
    ),
    SeedDocument(
        id="kb-shipping",
        title="Shipping Policy",
        category="orders",
        content=(
            "Standard shipping takes 3-7 business days. Express shipping takes 1-2 "
            "business days. Tracking is emailed when the order ships. Delays can occur "
            "during holidays. Contact support if a package is more than 2 days late."
        ),
    ),
    SeedDocument(
        id="kb-refunds",
        title="Refund Policy",
        category="billing",
        content=(
            "Refunds are available within 30 days of purchase for unused items. "
            "Refund requests require human approval. After approval, refunds post to "
            "the original payment method within 5-10 business days. Subscription "
            "cancellations take effect at the end of the current billing period."
        ),
    ),
    SeedDocument(
        id="kb-subscription",
        title="Subscription Plans",
        category="subscription",
        content=(
            "We offer Basic, Pro, and Business plans. You can change plans anytime from "
            "Account > Billing. Downgrades apply at the next renewal. Cancel anytime "
            "from Account > Subscription. Cancelled plans remain active until period end."
        ),
    ),
    SeedDocument(
        id="kb-wifi-troubleshoot",
        title="Wi-Fi Troubleshooting",
        category="technical",
        content=(
            "If you cannot connect to Wi-Fi: 1) Restart the router. 2) Forget the "
            "network and reconnect. 3) Update your network driver. 4) Try another "
            "device. 5) Contact support if the issue continues after these steps."
        ),
    ),
    SeedDocument(
        id="kb-hours",
        title="Support Hours",
        category="general",
        content=(
            "AI support is available 24/7. Human support agents are available Monday "
            "to Friday, 9:00 AM to 6:00 PM local time. Urgent billing or security "
            "issues are escalated immediately."
        ),
    ),
]


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def chunk_text(text: str, *, chunk_size: int = 500) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        chunks.append(cleaned[start : start + chunk_size])
        start += chunk_size
    return chunks


def _embed_chunk(title: str, content: str) -> str:
    return embedding_to_json(embed_text(f"{title}\n{content}"))


def ensure_seed_documents(db: Session) -> None:
    """Idempotently load built-in knowledge into the database."""
    for seed in SEED_DOCUMENTS:
        existing = db.get(KnowledgeDocument, seed.id)
        if existing is not None:
            # Backfill embeddings for older seed chunks.
            for chunk in existing.chunks:
                if not chunk.embedding_json:
                    chunk.embedding_json = _embed_chunk(chunk.title, chunk.content)
            continue
        doc = KnowledgeDocument(
            id=seed.id,
            name=seed.title,
            doc_type=DocumentType.TXT,
            category=seed.category,
            status=DocumentStatus.indexed,
            chunk_count=1,
            source="seed",
        )
        db.add(doc)
        db.add(
            KnowledgeChunk(
                document_id=seed.id,
                chunk_index=0,
                title=seed.title,
                content=seed.content,
                embedding_json=_embed_chunk(seed.title, seed.content),
            )
        )
    db.commit()


def index_document(
    db: Session,
    *,
    name: str,
    content: str,
    category: str = "general",
    doc_type: DocumentType = DocumentType.TXT,
    uploaded_by: str | None = None,
) -> KnowledgeDocument:
    doc = KnowledgeDocument(
        name=name,
        doc_type=doc_type,
        category=category,
        status=DocumentStatus.processing,
        uploaded_by=uploaded_by,
        source="upload",
    )
    db.add(doc)
    db.flush()

    parts = chunk_text(content)
    for index, part in enumerate(parts):
        db.add(
            KnowledgeChunk(
                document_id=doc.id,
                chunk_index=index,
                title=name,
                content=part,
                embedding_json=_embed_chunk(name, part),
            )
        )
    doc.chunk_count = len(parts)
    doc.status = DocumentStatus.indexed if parts else DocumentStatus.failed
    db.commit()
    db.refresh(doc)
    return doc


def reindex_embeddings(db: Session) -> int:
    """Compute embeddings for any chunks missing them. Returns updated count."""
    chunks = list(db.scalars(select(KnowledgeChunk)))
    updated = 0
    for chunk in chunks:
        if chunk.embedding_json:
            continue
        chunk.embedding_json = _embed_chunk(chunk.title, chunk.content)
        updated += 1
    if updated:
        db.commit()
    return updated


def search_knowledge(
    query: str,
    *,
    limit: int = 3,
    db: Session | None = None,
    min_similarity: float = 0.12,
) -> list[dict[str, object]]:
    """Rank knowledge chunks by vector cosine similarity (with keyword fallback)."""
    query_tokens = _tokenize(query)
    if not query.strip():
        return []

    query_vec = embed_text(query)
    candidates: list[tuple[float, dict[str, object]]] = []

    if db is not None:
        chunks = list(
            db.scalars(
                select(KnowledgeChunk).options(selectinload(KnowledgeChunk.document))
            )
        )
        for chunk in chunks:
            doc = chunk.document
            if doc is None or doc.status != DocumentStatus.indexed:
                continue

            stored = embedding_from_json(chunk.embedding_json)
            if stored is None:
                chunk.embedding_json = _embed_chunk(chunk.title, chunk.content)
                stored = embedding_from_json(chunk.embedding_json)

            score = cosine_similarity(query_vec, stored or [])

            # Blend a little keyword overlap so exact terms still rank well.
            if query_tokens:
                blob = f"{chunk.title} {doc.category} {chunk.content}"
                overlap = query_tokens & _tokenize(blob)
                if overlap:
                    keyword = len(overlap) / max(len(query_tokens), 1)
                    score = max(score, 0.65 * score + 0.35 * keyword)

            if score < min_similarity:
                continue

            candidates.append(
                (
                    score,
                    {
                        "document_id": doc.id,
                        "title": doc.name or chunk.title,
                        "category": doc.category,
                        "content": chunk.content,
                        "similarity": round(score, 3),
                    },
                )
            )
    else:
        for doc in SEED_DOCUMENTS:
            score = cosine_similarity(
                query_vec, embed_text(f"{doc.title}\n{doc.content}")
            )
            if query_tokens:
                overlap = query_tokens & _tokenize(
                    f"{doc.title} {doc.category} {doc.content}"
                )
                if overlap:
                    keyword = len(overlap) / max(len(query_tokens), 1)
                    score = max(score, 0.65 * score + 0.35 * keyword)
            if score < min_similarity:
                continue
            candidates.append(
                (
                    score,
                    {
                        "document_id": doc.id,
                        "title": doc.title,
                        "category": doc.category,
                        "content": doc.content,
                        "similarity": round(score, 3),
                    },
                )
            )

    candidates.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in candidates[:limit]]
