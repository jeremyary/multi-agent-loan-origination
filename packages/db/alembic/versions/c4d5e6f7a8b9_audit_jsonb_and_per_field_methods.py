# This project was developed with assistance from AI tools.
"""audit_events JSONB + per-field collection methods

- D10: audit_events.event_data Text -> JSONB (both public + hmda schemas)
- D15: hmda.demographics: replace collection_method with per-field method columns

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # D10: audit_events.event_data Text -> JSONB (public schema)
    op.execute(
        "ALTER TABLE audit_events "
        "ALTER COLUMN event_data TYPE JSONB USING event_data::jsonb"
    )

    # D10: audit_events.event_data Text -> JSONB (hmda schema)
    op.execute(
        "ALTER TABLE hmda.audit_events "
        "ALTER COLUMN event_data TYPE JSONB USING event_data::jsonb"
    )

    # D15: Add per-field method columns to hmda.demographics
    op.add_column(
        "demographics",
        sa.Column("race_method", sa.String(50), nullable=True),
        schema="hmda",
    )
    op.add_column(
        "demographics",
        sa.Column("ethnicity_method", sa.String(50), nullable=True),
        schema="hmda",
    )
    op.add_column(
        "demographics",
        sa.Column("sex_method", sa.String(50), nullable=True),
        schema="hmda",
    )
    op.add_column(
        "demographics",
        sa.Column("age_method", sa.String(50), nullable=True),
        schema="hmda",
    )

    # Migrate existing collection_method to all per-field columns
    op.execute(
        "UPDATE hmda.demographics SET "
        "race_method = collection_method, "
        "ethnicity_method = collection_method, "
        "sex_method = collection_method, "
        "age_method = collection_method"
    )

    # Drop the old single collection_method column
    op.drop_column("demographics", "collection_method", schema="hmda")


def downgrade() -> None:
    # Restore single collection_method column
    op.add_column(
        "demographics",
        sa.Column("collection_method", sa.String(50), nullable=False, server_default="self_reported"),
        schema="hmda",
    )

    # Copy race_method back as the single method (best approximation)
    op.execute(
        "UPDATE hmda.demographics SET collection_method = COALESCE(race_method, 'self_reported')"
    )

    # Drop per-field method columns
    op.drop_column("demographics", "age_method", schema="hmda")
    op.drop_column("demographics", "sex_method", schema="hmda")
    op.drop_column("demographics", "ethnicity_method", schema="hmda")
    op.drop_column("demographics", "race_method", schema="hmda")

    # D10: Revert JSONB -> Text
    op.execute(
        "ALTER TABLE hmda.audit_events "
        "ALTER COLUMN event_data TYPE TEXT USING event_data::text"
    )
    op.execute(
        "ALTER TABLE audit_events "
        "ALTER COLUMN event_data TYPE TEXT USING event_data::text"
    )
