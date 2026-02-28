# This project was developed with assistance from AI tools.
"""add rate_lock updated_at, denial_reasons jsonb

Revision ID: a509624ca371
Revises: c4d5e6f7a8b0
Create Date: 2026-02-27 19:08:37.895065

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a509624ca371'
down_revision = 'c4d5e6f7a8b0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'rate_locks',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    op.alter_column(
        'decisions',
        'denial_reasons',
        existing_type=sa.TEXT(),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
        postgresql_using='denial_reasons::jsonb',
    )


def downgrade() -> None:
    op.alter_column(
        'decisions',
        'denial_reasons',
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=sa.TEXT(),
        existing_nullable=True,
    )
    op.drop_column('rate_locks', 'updated_at')
