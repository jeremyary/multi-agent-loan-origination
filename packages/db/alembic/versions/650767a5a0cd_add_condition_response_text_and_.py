"""add condition response_text and document condition_id

Revision ID: 650767a5a0cd
Revises: b8c9d0e1f2a3
Create Date: 2026-02-25 18:52:44.265862

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "650767a5a0cd"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conditions", sa.Column("response_text", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("condition_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_documents_condition_id"), "documents", ["condition_id"], unique=False)
    op.create_foreign_key(
        "fk_documents_condition_id",
        "documents",
        "conditions",
        ["condition_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_documents_condition_id", "documents", type_="foreignkey")
    op.drop_index(op.f("ix_documents_condition_id"), table_name="documents")
    op.drop_column("documents", "condition_id")
    op.drop_column("conditions", "response_text")
