# This project was developed with assistance from AI tools.
"""restrict audit_events to append-only for lending_app and compliance_app

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-02-24 18:30:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The a1b2c3d4e5f6 migration grants GRANT ALL on all public tables to
    # lending_app, which includes UPDATE and DELETE on audit_events. This
    # violates the append-only audit guarantee. Revoke those privileges.
    op.execute("REVOKE UPDATE, DELETE ON audit_events FROM lending_app")
    op.execute("REVOKE UPDATE, DELETE ON audit_events FROM compliance_app")


def downgrade() -> None:
    op.execute("GRANT UPDATE, DELETE ON audit_events TO lending_app")
    op.execute("GRANT UPDATE, DELETE ON audit_events TO compliance_app")
