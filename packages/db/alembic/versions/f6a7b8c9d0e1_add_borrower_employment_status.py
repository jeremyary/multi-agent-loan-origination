# This project was developed with assistance from AI tools.
"""add borrower employment_status column

Revision ID: f6a7b8c9d0e1
Revises: c4d5e6f7a8b9
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "borrowers",
        sa.Column("employment_status", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("borrowers", "employment_status")
