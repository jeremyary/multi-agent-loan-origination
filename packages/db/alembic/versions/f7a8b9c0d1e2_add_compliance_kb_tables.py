# This project was developed with assistance from AI tools.
"""add compliance knowledge base tables

- Enable pgvector extension
- Create kb_documents table (tier 1=federal, 2=agency, 3=internal)
- Create kb_chunks table with vector(768) embedding column
- HNSW index on kb_chunks.embedding for cosine similarity search
- Grant lending_app CRUD, compliance_app SELECT on both tables

Revision ID: f7a8b9c0d1e2
Revises: a1b2c3d4e5f7
Create Date: 2026-02-27 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "f7a8b9c0d1e2"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # kb_documents table
    op.create_table(
        "kb_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kb_documents_tier", "kb_documents", ["tier"])

    # kb_chunks table
    op.create_table(
        "kb_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("section_ref", sa.String(500), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["kb_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kb_chunks_document_id", "kb_chunks", ["document_id"])

    # HNSW index for cosine similarity search
    op.execute(
        "CREATE INDEX ix_kb_chunks_embedding ON kb_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # Grants
    for table in ("kb_documents", "kb_chunks"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO lending_app")
        op.execute(f"GRANT SELECT ON {table} TO compliance_app")


def downgrade() -> None:
    op.drop_index("ix_kb_chunks_embedding", table_name="kb_chunks")
    op.drop_index("ix_kb_chunks_document_id", table_name="kb_chunks")
    op.drop_table("kb_chunks")
    op.drop_index("ix_kb_documents_tier", table_name="kb_documents")
    op.drop_table("kb_documents")
