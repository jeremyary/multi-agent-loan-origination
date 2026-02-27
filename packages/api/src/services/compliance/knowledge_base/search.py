# This project was developed with assistance from AI tools.
"""Compliance KB vector search with tier-based boosting.

Performs cosine similarity search via pgvector, applies tier boost
factors to prioritize federal regulations over internal policies,
and returns results with citation metadata.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.inference.client import get_embeddings

logger = logging.getLogger(__name__)

# Tier boost factors: federal > agency > internal
_TIER_BOOST = {1: 1.5, 2: 1.2, 3: 1.0}
_TIER_LABELS = {1: "Federal Regulation", 2: "Agency Guideline", 3: "Internal Policy"}
_MIN_SIMILARITY = 0.3


@dataclass
class KBSearchResult:
    """A single compliance KB search result with citation metadata."""

    chunk_text: str
    source_document: str
    section_ref: str | None
    tier: int
    tier_label: str
    similarity: float
    boosted_similarity: float
    effective_date: str | None


async def search_kb(
    session: AsyncSession,
    query: str,
    top_k: int = 5,
) -> list[KBSearchResult]:
    """Search the compliance KB using vector similarity with tier boosting.

    Args:
        session: Database session.
        query: Search query text.
        top_k: Number of results to return after boosting.

    Returns:
        List of KBSearchResult ordered by boosted similarity (descending).
    """
    # Get query embedding
    try:
        embeddings = await get_embeddings([query])
        query_vec = embeddings[0]
    except Exception:
        logger.warning("Failed to get query embedding, returning empty results")
        return []

    # Fetch top_k * 3 candidates from DB, apply boost, re-sort, truncate
    fetch_limit = top_k * 3

    sql = text("""
        SELECT c.id, c.chunk_text, c.section_ref, d.title, d.tier,
               d.effective_date,
               1 - (c.embedding <=> :query_vec) AS similarity
        FROM kb_chunks c
        JOIN kb_documents d ON c.document_id = d.id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> :query_vec
        LIMIT :fetch_limit
    """)

    result = await session.execute(
        sql,
        {"query_vec": str(query_vec), "fetch_limit": fetch_limit},
    )
    rows = result.fetchall()

    # Apply tier boost and filter by minimum similarity
    results: list[KBSearchResult] = []
    for row in rows:
        similarity = float(row.similarity)
        if similarity < _MIN_SIMILARITY:
            continue

        tier = row.tier
        boost = _TIER_BOOST.get(tier, 1.0)
        boosted = similarity * boost

        results.append(
            KBSearchResult(
                chunk_text=row.chunk_text,
                source_document=row.title,
                section_ref=row.section_ref,
                tier=tier,
                tier_label=_TIER_LABELS.get(tier, f"Tier {tier}"),
                similarity=similarity,
                boosted_similarity=boosted,
                effective_date=str(row.effective_date) if row.effective_date else None,
            )
        )

    # Sort by boosted similarity descending, truncate to top_k
    results.sort(key=lambda r: r.boosted_similarity, reverse=True)
    return results[:top_k]
