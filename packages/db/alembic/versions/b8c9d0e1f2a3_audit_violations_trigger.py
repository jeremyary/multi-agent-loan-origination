# This project was developed with assistance from AI tools.
"""add audit_violations table and append-only trigger on audit_events

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None

TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION audit_events_prevent_mutation()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_violations (attempted_operation, db_user, audit_event_id)
    VALUES (TG_OP, current_user, OLD.id);

    RAISE EXCEPTION 'audit_events is append-only: % denied for row %', TG_OP, OLD.id;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

TRIGGER_UPDATE = """
CREATE TRIGGER audit_events_no_update
    BEFORE UPDATE ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION audit_events_prevent_mutation();
"""

TRIGGER_DELETE = """
CREATE TRIGGER audit_events_no_delete
    BEFORE DELETE ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION audit_events_prevent_mutation();
"""


def upgrade() -> None:
    op.create_table(
        "audit_violations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("attempted_operation", sa.String(10), nullable=False),
        sa.Column("db_user", sa.String(255), nullable=False),
        sa.Column("audit_event_id", sa.Integer, nullable=True),
    )

    op.execute(TRIGGER_FUNCTION)
    op.execute(TRIGGER_UPDATE)
    op.execute(TRIGGER_DELETE)

    # Grant SELECT + INSERT on audit_violations to app roles so the trigger
    # can insert rows when running as lending_app or compliance_app.
    op.execute("GRANT SELECT, INSERT ON audit_violations TO lending_app")
    op.execute("GRANT SELECT, INSERT ON audit_violations TO compliance_app")
    op.execute(
        "GRANT USAGE, SELECT ON SEQUENCE audit_violations_id_seq TO lending_app"
    )
    op.execute(
        "GRANT USAGE, SELECT ON SEQUENCE audit_violations_id_seq TO compliance_app"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_delete ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_prevent_mutation()")
    op.drop_table("audit_violations")
