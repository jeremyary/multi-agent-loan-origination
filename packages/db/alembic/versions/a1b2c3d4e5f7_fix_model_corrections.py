# This project was developed with assistance from AI tools.
"""fix: model corrections for pre-phase-3 audit

- Rename borrowers.ssn_encrypted -> ssn (C-7: column name misleading)
- Add index on audit_events.session_id (W-4: full table scans)
- Add partial unique index on application_borrowers for is_primary (S-18)
- Change Float -> Numeric for rates and ratios (S-19):
  - application_financials.dti_ratio: Numeric(5,4)
  - rate_locks.locked_rate: Numeric(5,3)
  - hmda.loan_data.dti_ratio: Numeric(5,4)
  - hmda.loan_data.interest_rate: Numeric(5,3)

Revision ID: a1b2c3d4e5f7
Revises: 650767a5a0cd
Create Date: 2026-02-26 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f7"
down_revision = "650767a5a0cd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # C-7: Rename ssn_encrypted -> ssn
    op.alter_column(
        "borrowers",
        "ssn_encrypted",
        new_column_name="ssn",
    )

    # W-4: Add index on audit_events.session_id
    op.create_index(
        "ix_audit_events_session_id",
        "audit_events",
        ["session_id"],
    )

    # S-18: Partial unique index -- one primary borrower per application
    op.create_index(
        "ix_app_borrower_unique_primary",
        "application_borrowers",
        ["application_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = true"),
    )

    # S-19: Float -> Numeric for financial precision
    op.alter_column(
        "application_financials",
        "dti_ratio",
        type_=sa.Numeric(5, 4),
        existing_type=sa.Float(),
        existing_nullable=True,
    )
    op.alter_column(
        "rate_locks",
        "locked_rate",
        type_=sa.Numeric(5, 3),
        existing_type=sa.Float(),
        existing_nullable=False,
    )
    op.alter_column(
        "loan_data",
        "dti_ratio",
        type_=sa.Numeric(5, 4),
        existing_type=sa.Float(),
        existing_nullable=True,
        schema="hmda",
    )
    op.alter_column(
        "loan_data",
        "interest_rate",
        type_=sa.Numeric(5, 3),
        existing_type=sa.Float(),
        existing_nullable=True,
        schema="hmda",
    )


def downgrade() -> None:
    # Reverse S-19: Numeric -> Float
    op.alter_column(
        "loan_data",
        "interest_rate",
        type_=sa.Float(),
        existing_type=sa.Numeric(5, 3),
        existing_nullable=True,
        schema="hmda",
    )
    op.alter_column(
        "loan_data",
        "dti_ratio",
        type_=sa.Float(),
        existing_type=sa.Numeric(5, 4),
        existing_nullable=True,
        schema="hmda",
    )
    op.alter_column(
        "rate_locks",
        "locked_rate",
        type_=sa.Float(),
        existing_type=sa.Numeric(5, 3),
        existing_nullable=False,
    )
    op.alter_column(
        "application_financials",
        "dti_ratio",
        type_=sa.Float(),
        existing_type=sa.Numeric(5, 4),
        existing_nullable=True,
    )

    # Reverse S-18
    op.drop_index(
        "ix_app_borrower_unique_primary",
        table_name="application_borrowers",
    )

    # Reverse W-4
    op.drop_index(
        "ix_audit_events_session_id",
        table_name="audit_events",
    )

    # Reverse C-7
    op.alter_column(
        "borrowers",
        "ssn",
        new_column_name="ssn_encrypted",
    )
