# This project was developed with assistance from AI tools.
"""add hmda schema and roles

Revision ID: a1b2c3d4e5f6
Revises: fe5adcef3769
Create Date: 2026-02-24 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "fe5adcef3769"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create hmda schema
    op.execute("CREATE SCHEMA IF NOT EXISTS hmda")

    # 2. Create demographics table in hmda schema
    op.create_table(
        "demographics",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("application_id", sa.Integer, nullable=False, index=True),
        sa.Column("race", sa.String(100), nullable=True),
        sa.Column("ethnicity", sa.String(100), nullable=True),
        sa.Column("sex", sa.String(50), nullable=True),
        sa.Column(
            "collection_method",
            sa.String(50),
            nullable=False,
            server_default="self_reported",
        ),
        sa.Column(
            "collected_at", sa.DateTime, server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime, server_default=sa.func.now(), nullable=False
        ),
        schema="hmda",
    )

    # 3. Grant lending_app full CRUD on public schema (existing + future tables)
    op.execute("GRANT USAGE ON SCHEMA public TO lending_app")
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO lending_app")
    op.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO lending_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO lending_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO lending_app"
    )

    # 4. Grant compliance_app SELECT-only on public schema
    op.execute("GRANT USAGE ON SCHEMA public TO compliance_app")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO compliance_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO compliance_app"
    )

    # 5. Grant compliance_app full CRUD on hmda schema
    op.execute("GRANT ALL ON SCHEMA hmda TO compliance_app")
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA hmda TO compliance_app")
    op.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA hmda TO compliance_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA hmda GRANT ALL ON TABLES TO compliance_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA hmda GRANT ALL ON SEQUENCES TO compliance_app"
    )

    # 6. Explicitly deny lending_app access to hmda schema
    op.execute("REVOKE ALL ON SCHEMA hmda FROM lending_app")

    # 7. Both roles can INSERT+SELECT on audit_events (+ sequence for autoincrement)
    op.execute("GRANT INSERT, SELECT ON audit_events TO lending_app")
    op.execute("GRANT INSERT, SELECT ON audit_events TO compliance_app")
    op.execute("GRANT USAGE ON SEQUENCE audit_events_id_seq TO lending_app")
    op.execute("GRANT USAGE ON SEQUENCE audit_events_id_seq TO compliance_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS hmda.demographics")
    op.execute("DROP SCHEMA IF EXISTS hmda")
    # Role grants are left in place (roles persist across migrations)
