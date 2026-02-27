# This project was developed with assistance from AI tools.
"""add TRID date columns to applications

- le_delivery_date: when Loan Estimate was delivered
- cd_delivery_date: when Closing Disclosure was delivered
- closing_date: scheduled closing date

Revision ID: a2b3c4d5e6f7
Revises: f7a8b9c0d1e2
Create Date: 2026-02-27 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a2b3c4d5e6f7"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("le_delivery_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("cd_delivery_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("closing_date", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("applications", "closing_date")
    op.drop_column("applications", "cd_delivery_date")
    op.drop_column("applications", "le_delivery_date")
