# This project was developed with assistance from AI tools.
"""hmda: add age column and loan_data table

Add age column to hmda.demographics for HMDA-reportable age data.
Create hmda.loan_data table for non-demographic HMDA fields that are
snapshotted at underwriting submission.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-25 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add age column to hmda.demographics
    op.add_column(
        "demographics",
        sa.Column("age", sa.String(20), nullable=True),
        schema="hmda",
    )

    # 2. Create hmda.loan_data table
    op.create_table(
        "loan_data",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("application_id", sa.Integer, nullable=False, unique=True, index=True),
        sa.Column("gross_monthly_income", sa.Numeric(12, 2), nullable=True),
        sa.Column("dti_ratio", sa.Float, nullable=True),
        sa.Column("credit_score", sa.Integer, nullable=True),
        sa.Column("loan_type", sa.String(50), nullable=True),
        sa.Column("loan_purpose", sa.String(50), nullable=True),
        sa.Column("property_location", sa.Text, nullable=True),
        sa.Column("interest_rate", sa.Float, nullable=True),
        sa.Column("total_fees", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "snapshot_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="hmda",
    )

    # 3. Grant compliance_app full access to the new table
    op.execute("GRANT INSERT, SELECT, UPDATE ON hmda.loan_data TO compliance_app")
    op.execute("GRANT USAGE ON SEQUENCE hmda.loan_data_id_seq TO compliance_app")

    # 4. Deny lending_app access (consistent with hmda.demographics)
    # lending_app already has REVOKE ALL ON SCHEMA hmda, but explicit for clarity
    op.execute("REVOKE ALL ON hmda.loan_data FROM lending_app")


def downgrade() -> None:
    op.drop_table("loan_data", schema="hmda")
    op.drop_column("demographics", "age", schema="hmda")
