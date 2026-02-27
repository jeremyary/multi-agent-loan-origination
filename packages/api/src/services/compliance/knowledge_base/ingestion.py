# This project was developed with assistance from AI tools.
"""Compliance KB ingestion pipeline.

Reads markdown files from data/compliance-kb/, parses YAML frontmatter,
chunks by section headers with paragraph-boundary splitting for long
sections, embeds via the embedding model tier, and stores in the DB.

Idempotent: clear_kb_content() removes all KB data before re-ingestion.
"""

import logging
import re
from pathlib import Path

from db import KBChunk, KBDocument
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.inference.client import get_embeddings

logger = logging.getLogger(__name__)

# Approximate token target for chunks (chars / 4 ≈ tokens)
_TARGET_CHUNK_CHARS = 512 * 4  # ~512 tokens
_OVERLAP_CHARS = 64 * 4  # ~64 tokens

# Tier directory mapping
_TIER_DIRS = {
    1: "tier1-federal",
    2: "tier2-agency",
    3: "tier3-internal",
}

_KB_DATA_ROOT = Path(__file__).resolve().parents[6] / "data" / "compliance-kb"


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Extract YAML frontmatter from markdown content.

    Args:
        content: Raw markdown file content.

    Returns:
        Tuple of (metadata dict, body text without frontmatter).
    """
    if not content.startswith("---"):
        return {}, content

    end = content.find("---", 3)
    if end == -1:
        return {}, content

    frontmatter_text = content[3:end].strip()
    body = content[end + 3 :].strip()

    metadata: dict[str, str] = {}
    for line in frontmatter_text.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            metadata[key.strip()] = value.strip().strip('"').strip("'")

    return metadata, body


def _chunk_markdown(body: str) -> list[dict[str, str]]:
    """Split markdown body into chunks by ## section headers.

    Long sections are further split at paragraph boundaries to stay
    near the target chunk size. Each chunk carries a section_ref
    from its nearest ## header.

    Args:
        body: Markdown body text (without frontmatter).

    Returns:
        List of dicts with 'text' and 'section_ref' keys.
    """
    # Split into sections by ## headers
    sections: list[tuple[str, str]] = []
    current_header = ""
    current_lines: list[str] = []

    for line in body.split("\n"):
        if line.startswith("## "):
            if current_lines:
                sections.append((current_header, "\n".join(current_lines).strip()))
            current_header = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_header, "\n".join(current_lines).strip()))

    # Split long sections at paragraph boundaries
    chunks: list[dict[str, str]] = []
    for header, text in sections:
        if not text:
            continue

        if len(text) <= _TARGET_CHUNK_CHARS:
            chunks.append({"text": text, "section_ref": header or None})
        else:
            paragraphs = re.split(r"\n\n+", text)
            current_chunk: list[str] = []
            current_len = 0

            for para in paragraphs:
                para_len = len(para)
                if current_len + para_len > _TARGET_CHUNK_CHARS and current_chunk:
                    chunks.append(
                        {
                            "text": "\n\n".join(current_chunk),
                            "section_ref": header or None,
                        }
                    )
                    # Overlap: keep last paragraph if it's not too long
                    if len(current_chunk[-1]) <= _OVERLAP_CHARS:
                        current_chunk = [current_chunk[-1]]
                        current_len = len(current_chunk[0])
                    else:
                        current_chunk = []
                        current_len = 0

                current_chunk.append(para)
                current_len += para_len

            if current_chunk:
                chunks.append(
                    {
                        "text": "\n\n".join(current_chunk),
                        "section_ref": header or None,
                    }
                )

    return chunks


async def clear_kb_content(session: AsyncSession) -> None:
    """Delete all KB chunks and documents."""
    await session.execute(delete(KBChunk))
    await session.execute(delete(KBDocument))
    await session.flush()
    logger.info("Cleared all KB content")


async def ingest_kb_content(
    session: AsyncSession,
    data_root: Path | None = None,
) -> dict[str, int]:
    """Ingest compliance KB markdown files into the database.

    Reads files from data/compliance-kb/{tier}/*.md, parses frontmatter,
    chunks text, generates embeddings, and stores everything.

    Args:
        session: Database session.
        data_root: Override path to KB data directory (for testing).

    Returns:
        Summary dict with document and chunk counts.
    """
    root = data_root or _KB_DATA_ROOT
    total_docs = 0
    total_chunks = 0

    for tier, dir_name in _TIER_DIRS.items():
        tier_path = root / dir_name
        if not tier_path.exists():
            logger.warning("KB tier directory not found: %s", tier_path)
            continue

        for md_file in sorted(tier_path.glob("*.md")):
            content = md_file.read_text()
            metadata, body = _parse_frontmatter(content)

            doc = KBDocument(
                title=metadata.get("title", md_file.stem),
                tier=tier,
                source_file=str(md_file.relative_to(root)),
                description=metadata.get("description"),
                effective_date=metadata.get("effective_date"),
            )
            session.add(doc)
            await session.flush()  # Get doc.id

            chunks = _chunk_markdown(body)
            chunk_texts = [c["text"] for c in chunks]

            # Attempt embedding
            embeddings: list[list[float]] | None = None
            if chunk_texts:
                try:
                    embeddings = await get_embeddings(chunk_texts)
                except Exception:
                    logger.warning(
                        "Embedding failed for %s, storing chunks without embeddings",
                        md_file.name,
                    )

            for i, chunk_data in enumerate(chunks):
                embedding = embeddings[i] if embeddings and i < len(embeddings) else None
                chunk = KBChunk(
                    document_id=doc.id,
                    chunk_text=chunk_data["text"],
                    section_ref=chunk_data["section_ref"],
                    chunk_index=i,
                    embedding=embedding,
                )
                session.add(chunk)

            total_docs += 1
            total_chunks += len(chunks)
            logger.info(
                "Ingested %s: %d chunks (tier %d)",
                md_file.name,
                len(chunks),
                tier,
            )

    await session.flush()
    logger.info("KB ingestion complete: %d documents, %d chunks", total_docs, total_chunks)
    return {"documents": total_docs, "chunks": total_chunks}
