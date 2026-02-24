# This project was developed with assistance from AI tools.
"""timestamps with timezone

All DateTime columns migrated from TIMESTAMP WITHOUT TIME ZONE to
TIMESTAMP WITH TIME ZONE for consistent timezone handling across
development environments and deployments.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-24 11:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

# All (table, column) pairs to migrate.
_COLUMNS = [
    ("borrowers", "dob"),
    ("borrowers", "created_at"),
    ("borrowers", "updated_at"),
    ("applications", "created_at"),
    ("applications", "updated_at"),
    ("application_financials", "created_at"),
    ("application_financials", "updated_at"),
    ("rate_locks", "lock_date"),
    ("rate_locks", "expiration_date"),
    ("rate_locks", "created_at"),
    ("conditions", "created_at"),
    ("conditions", "updated_at"),
    ("decisions", "created_at"),
    ("documents", "created_at"),
    ("documents", "updated_at"),
    ("document_extractions", "created_at"),
    ("audit_events", "timestamp"),
    ("demo_data_manifest", "seeded_at"),
]

_HMDA_COLUMNS = [
    ("demographics", "collected_at"),
    ("demographics", "created_at"),
]


def upgrade() -> None:
    for table, column in _COLUMNS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN "{column}" '
            f"TYPE TIMESTAMP WITH TIME ZONE "
            f'USING "{column}" AT TIME ZONE \'UTC\''
        )

    for table, column in _HMDA_COLUMNS:
        op.execute(
            f'ALTER TABLE hmda.{table} ALTER COLUMN "{column}" '
            f"TYPE TIMESTAMP WITH TIME ZONE "
            f'USING "{column}" AT TIME ZONE \'UTC\''
        )


def downgrade() -> None:
    for table, column in _COLUMNS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN "{column}" '
            f"TYPE TIMESTAMP WITHOUT TIME ZONE"
        )

    for table, column in _HMDA_COLUMNS:
        op.execute(
            f'ALTER TABLE hmda.{table} ALTER COLUMN "{column}" '
            f"TYPE TIMESTAMP WITHOUT TIME ZONE"
        )
