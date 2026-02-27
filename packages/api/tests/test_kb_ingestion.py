# This project was developed with assistance from AI tools.
"""Tests for compliance KB ingestion pipeline."""

import textwrap
from unittest.mock import AsyncMock

import pytest
from db import KBChunk
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.compliance.knowledge_base.ingestion import (
    _chunk_markdown,
    _parse_frontmatter,
    ingest_kb_content,
)


class TestParseFrontmatter:
    """Tests for YAML frontmatter parsing."""

    def test_extracts_title_and_date(self):
        content = textwrap.dedent("""\
            ---
            title: "Test Regulation"
            effective_date: "2024-01-01"
            ---
            Body text here.
        """)
        metadata, body = _parse_frontmatter(content)
        assert metadata["title"] == "Test Regulation"
        assert metadata["effective_date"] == "2024-01-01"

    def test_returns_body_without_frontmatter(self):
        content = textwrap.dedent("""\
            ---
            title: "Test"
            ---
            ## Section One

            Content here.
        """)
        metadata, body = _parse_frontmatter(content)
        assert body.startswith("## Section One")
        assert "---" not in body

    def test_handles_no_frontmatter(self):
        content = "Just plain text with no frontmatter."
        metadata, body = _parse_frontmatter(content)
        assert metadata == {}
        assert body == content

    def test_handles_empty_frontmatter(self):
        content = "---\n---\nBody text."
        metadata, body = _parse_frontmatter(content)
        assert metadata == {}
        assert body == "Body text."


class TestChunkMarkdown:
    """Tests for markdown chunking."""

    def test_splits_on_section_headers(self):
        body = textwrap.dedent("""\
            ## Section One

            Content for section one.

            ## Section Two

            Content for section two.
        """)
        chunks = _chunk_markdown(body)
        assert len(chunks) == 2
        assert "section one" in chunks[0]["text"].lower()
        assert "section two" in chunks[1]["text"].lower()

    def test_preserves_section_ref(self):
        body = textwrap.dedent("""\
            ## DTI Limits

            The maximum DTI ratio is 43%.

            ## Credit Score

            Minimum credit score is 620.
        """)
        chunks = _chunk_markdown(body)
        assert chunks[0]["section_ref"] == "DTI Limits"
        assert chunks[1]["section_ref"] == "Credit Score"

    def test_splits_long_sections(self):
        # Create a section with many paragraphs exceeding target chunk size
        paragraphs = [f"Paragraph {i}. " + "x" * 300 for i in range(20)]
        body = "## Long Section\n\n" + "\n\n".join(paragraphs)
        chunks = _chunk_markdown(body)
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk["section_ref"] == "Long Section"

    def test_handles_content_before_first_header(self):
        body = textwrap.dedent("""\
            Intro text before any headers.

            ## First Section

            Section content.
        """)
        chunks = _chunk_markdown(body)
        assert len(chunks) == 2
        assert chunks[0]["section_ref"] is None or chunks[0]["section_ref"] == ""
        assert chunks[1]["section_ref"] == "First Section"

    def test_empty_body(self):
        chunks = _chunk_markdown("")
        assert chunks == []


class TestIngestKbContent:
    """Tests for the full ingestion pipeline (mocked DB + embeddings)."""

    @pytest.fixture
    def kb_data_dir(self, tmp_path):
        """Create a temporary KB data directory with test content."""
        tier1 = tmp_path / "tier1-federal"
        tier1.mkdir()
        (tier1 / "test-reg.md").write_text(
            textwrap.dedent("""\
            ---
            title: "Test Regulation"
            source_document: "Test Source"
            effective_date: "2024-01-01"
            ---

            DISCLAIMER: Simulated content.

            ## Section A

            Content for section A.

            ## Section B

            Content for section B.
        """)
        )
        tier3 = tmp_path / "tier3-internal"
        tier3.mkdir()
        (tier3 / "test-policy.md").write_text(
            textwrap.dedent("""\
            ---
            title: "Test Policy"
            source_document: "Internal Manual"
            ---

            ## Policy Section

            Policy content here.
        """)
        )
        return tmp_path

    @pytest.mark.asyncio
    async def test_creates_documents_and_chunks(self, kb_data_dir, monkeypatch):
        """Ingestion creates KBDocument and KBChunk rows with embeddings."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = lambda x: None
        mock_session.flush = AsyncMock()

        fake_embeddings = [[0.1] * 768, [0.2] * 768, [0.3] * 768]
        mock_embed = AsyncMock(return_value=fake_embeddings)

        import src.services.compliance.knowledge_base.ingestion as mod

        monkeypatch.setattr(mod, "get_embeddings", mock_embed)

        result = await ingest_kb_content(mock_session, data_root=kb_data_dir)

        assert result["documents"] == 2  # test-reg.md + test-policy.md
        assert result["chunks"] >= 3  # at least 3 chunks across both files
        assert mock_embed.call_count >= 1

    @pytest.mark.asyncio
    async def test_handles_embedding_failure(self, kb_data_dir, monkeypatch):
        """When embedding fails, chunks are stored with None embedding."""
        mock_session = AsyncMock(spec=AsyncSession)
        added_objects = []
        mock_session.add = lambda x: added_objects.append(x)
        mock_session.flush = AsyncMock()

        mock_embed = AsyncMock(side_effect=RuntimeError("No embedding model"))

        import src.services.compliance.knowledge_base.ingestion as mod

        monkeypatch.setattr(mod, "get_embeddings", mock_embed)

        result = await ingest_kb_content(mock_session, data_root=kb_data_dir)

        assert result["documents"] == 2
        assert result["chunks"] >= 3

        # Verify chunks were added without embeddings
        chunk_objects = [o for o in added_objects if isinstance(o, KBChunk)]
        for chunk in chunk_objects:
            assert chunk.embedding is None
