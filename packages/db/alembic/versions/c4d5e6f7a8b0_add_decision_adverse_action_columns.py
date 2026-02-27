# This project was developed with assistance from AI tools.
"""add decision adverse action columns

- ai_agreement: whether UW decision agrees with AI recommendation
- override_rationale: explanation when UW overrides AI
- denial_reasons: JSON-serialized list of denial reason strings
- credit_score_used: credit score at time of decision
- credit_score_source: credit bureau source
- contributing_factors: factors that contributed to the decision

Revision ID: c4d5e6f7a8b0
Revises: b3c4d5e6f7a9
Create Date: 2026-02-27 22:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b0"
down_revision = "b3c4d5e6f7a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("decisions", sa.Column("ai_agreement", sa.Boolean(), nullable=True))
    op.add_column("decisions", sa.Column("override_rationale", sa.Text(), nullable=True))
    op.add_column("decisions", sa.Column("denial_reasons", sa.Text(), nullable=True))
    op.add_column("decisions", sa.Column("credit_score_used", sa.Integer(), nullable=True))
    op.add_column(
        "decisions", sa.Column("credit_score_source", sa.String(100), nullable=True)
    )
    op.add_column("decisions", sa.Column("contributing_factors", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("decisions", "contributing_factors")
    op.drop_column("decisions", "credit_score_source")
    op.drop_column("decisions", "credit_score_used")
    op.drop_column("decisions", "denial_reasons")
    op.drop_column("decisions", "override_rationale")
    op.drop_column("decisions", "ai_agreement")
