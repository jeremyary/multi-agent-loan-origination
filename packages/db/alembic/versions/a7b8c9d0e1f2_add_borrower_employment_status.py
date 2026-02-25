# This project was developed with assistance from AI tools.
"""add borrower employment_status column

Revision ID: a7b8c9d0e1f2
Revises: d5e6f7a8b9c0
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "borrowers",
        sa.Column("employment_status", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("borrowers", "employment_status")
