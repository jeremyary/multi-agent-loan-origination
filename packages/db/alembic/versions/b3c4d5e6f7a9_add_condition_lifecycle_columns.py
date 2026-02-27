# This project was developed with assistance from AI tools.
"""add condition lifecycle columns

- due_date: optional deadline for the condition
- iteration_count: tracks return/resubmit cycles
- waiver_rationale: reason text when a condition is waived

Revision ID: b3c4d5e6f7a9
Revises: a2b3c4d5e6f7
Create Date: 2026-02-27 20:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b3c4d5e6f7a9"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conditions", sa.Column("due_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "conditions",
        sa.Column("iteration_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("conditions", sa.Column("waiver_rationale", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("conditions", "waiver_rationale")
    op.drop_column("conditions", "iteration_count")
    op.drop_column("conditions", "due_date")
