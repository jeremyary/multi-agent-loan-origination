# This project was developed with assistance from AI tools.
"""per-borrower financials

D21: Add borrower_id to application_financials for per-borrower tracking.
Drop unique constraint on application_id, replace with composite unique.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa

revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add borrower_id column
    op.add_column(
        "application_financials",
        sa.Column(
            "borrower_id",
            sa.Integer(),
            sa.ForeignKey("borrowers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_application_financials_borrower_id",
        "application_financials",
        ["borrower_id"],
    )

    # Drop the single-column unique constraint on application_id
    op.drop_constraint(
        "application_financials_application_id_key",
        "application_financials",
        type_="unique",
    )

    # Add composite unique constraint (application_id, borrower_id)
    op.create_unique_constraint(
        "uq_app_financials_app_borrower",
        "application_financials",
        ["application_id", "borrower_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_app_financials_app_borrower",
        "application_financials",
        type_="unique",
    )
    op.drop_index("ix_application_financials_borrower_id", "application_financials")
    op.drop_column("application_financials", "borrower_id")

    # Restore single unique constraint on application_id
    op.create_unique_constraint(
        "application_financials_application_id_key",
        "application_financials",
        ["application_id"],
    )
