# This project was developed with assistance from AI tools.
"""add co-borrower support

Create application_borrowers junction table, add borrower_id to documents,
drop borrower_id from applications.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-02-25 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create application_borrowers junction table
    op.create_table(
        "application_borrowers",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "application_id",
            sa.Integer,
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "borrower_id",
            sa.Integer,
            sa.ForeignKey("borrowers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("application_id", "borrower_id", name="uq_app_borrower"),
    )

    # 2. Add borrower_id to documents (nullable, for linking docs to specific borrowers)
    op.add_column(
        "documents",
        sa.Column(
            "borrower_id",
            sa.Integer,
            sa.ForeignKey("borrowers.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # 3. Drop borrower_id from applications
    op.drop_constraint("applications_borrower_id_fkey", "applications", type_="foreignkey")
    op.drop_index("ix_applications_borrower_id", table_name="applications")
    op.drop_column("applications", "borrower_id")


def downgrade() -> None:
    # Re-add borrower_id to applications
    op.add_column(
        "applications",
        sa.Column(
            "borrower_id",
            sa.Integer,
            sa.ForeignKey("borrowers.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    op.create_index("ix_applications_borrower_id", "applications", ["borrower_id"])

    # Drop borrower_id from documents
    op.drop_column("documents", "borrower_id")

    # Drop junction table
    op.drop_table("application_borrowers")
