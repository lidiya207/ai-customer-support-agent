"""Local hashed embeddings + cosine similarity (works with MySQL, no pgvector)."""

from __future__ import annotations

import hashlib
import json
import math
import re

EMBED_DIM = 384


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1]


def embed_text(text: str, *, dim: int = EMBED_DIM) -> list[float]:
    """
    Deterministic bag-of-tokens embedding via the hashing trick.

    Good enough for MVP vector search without an external embedding service.
    Tokens and bigrams are hashed into a fixed-size vector and L2-normalized.
    """
    vec = [0.0] * dim
    tokens = _tokenize(text)
    if not tokens:
        return vec

    features = list(tokens)
    features.extend(f"{a}_{b}" for a, b in zip(tokens, tokens[1:]))

    for feature in features:
        digest = hashlib.sha256(feature.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % dim
        sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


def embedding_to_json(vec: list[float]) -> str:
    return json.dumps(vec)


def embedding_from_json(raw: str | None) -> list[float] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(data, list) or not data:
        return None
    try:
        return [float(x) for x in data]
    except (TypeError, ValueError):
        return None
