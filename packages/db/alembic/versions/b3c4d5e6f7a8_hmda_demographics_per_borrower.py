# This project was developed with assistance from AI tools.
"""hmda demographics per-borrower: add borrower_id, updated_at, unique constraint

Revision ID: b3c4d5e6f7a8
Revises: f6a7b8c9d0e1
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa

revision = "b3c4d5e6f7a8"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add borrower_id column (no FK -- hmda schema cannot reference public.borrowers)
    op.add_column(
        "demographics",
        sa.Column("borrower_id", sa.Integer(), nullable=True),
        schema="hmda",
    )
    op.create_index(
        "ix_demographics_borrower_id",
        "demographics",
        ["borrower_id"],
        schema="hmda",
    )

    # Add updated_at column
    op.add_column(
        "demographics",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="hmda",
    )

    # Unique constraint on (application_id, borrower_id)
    # PostgreSQL treats NULLs as distinct, so legacy rows with NULL borrower_id won't conflict
    op.create_unique_constraint(
        "uq_demographics_app_borrower",
        "demographics",
        ["application_id", "borrower_id"],
        schema="hmda",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_demographics_app_borrower",
        "demographics",
        schema="hmda",
    )
    op.drop_index(
        "ix_demographics_borrower_id",
        table_name="demographics",
        schema="hmda",
    )
    op.drop_column("demographics", "updated_at", schema="hmda")
    op.drop_column("demographics", "borrower_id", schema="hmda")
