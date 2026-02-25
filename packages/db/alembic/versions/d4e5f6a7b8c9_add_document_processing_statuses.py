# This project was developed with assistance from AI tools.
"""add document processing statuses

Add PROCESSING, PROCESSING_COMPLETE, PROCESSING_FAILED values to
the DocumentStatus enum for upload-to-review lifecycle tracking.

The documents.status column is VARCHAR(50) (not a native PostgreSQL
enum), so the new values are accepted without a schema change. This
migration serves as a merge point for the two prior branches and a
marker that the new statuses are intentional.

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a7, c3d4e5f6a7b8
Create Date: 2026-02-24 18:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = ("b2c3d4e5f6a7", "c3d4e5f6a7b8")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # documents.status is VARCHAR(50) -- no schema change needed.
    # New enum values (processing, processing_complete, processing_failed)
    # are enforced by the application layer via the Python DocumentStatus enum.
    pass


def downgrade() -> None:
    pass
