# This project was developed with assistance from AI tools.
"""add domain models

Revision ID: fe5adcef3769
Revises:
Create Date: 2026-02-23 14:33:59.140027

"""

import sqlalchemy as sa
from alembic import op

revision = "fe5adcef3769"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "borrowers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("keycloak_user_id", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("ssn_encrypted", sa.String(255), nullable=True),
        sa.Column("dob", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keycloak_user_id"),
    )
    op.create_index("ix_borrowers_keycloak_user_id", "borrowers", ["keycloak_user_id"])
    op.create_index("ix_borrowers_email", "borrowers", ["email"])

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("borrower_id", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False, server_default="inquiry"),
        sa.Column("loan_type", sa.String(50), nullable=True),
        sa.Column("property_address", sa.Text(), nullable=True),
        sa.Column("loan_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("property_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("assigned_to", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["borrower_id"], ["borrowers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_applications_borrower_id", "applications", ["borrower_id"])
    op.create_index("ix_applications_assigned_to", "applications", ["assigned_to"])

    op.create_table(
        "application_financials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("gross_monthly_income", sa.Numeric(12, 2), nullable=True),
        sa.Column("monthly_debts", sa.Numeric(12, 2), nullable=True),
        sa.Column("total_assets", sa.Numeric(14, 2), nullable=True),
        sa.Column("credit_score", sa.Integer(), nullable=True),
        sa.Column("dti_ratio", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id"),
    )
    op.create_index(
        "ix_application_financials_application_id", "application_financials", ["application_id"]
    )

    op.create_table(
        "rate_locks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("locked_rate", sa.Float(), nullable=False),
        sa.Column("lock_date", sa.DateTime(), nullable=False),
        sa.Column("expiration_date", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rate_locks_application_id", "rate_locks", ["application_id"])

    op.create_table(
        "conditions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("issued_by", sa.String(255), nullable=True),
        sa.Column("cleared_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conditions_application_id", "conditions", ["application_id"])

    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("decision_type", sa.String(50), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("ai_recommendation", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decisions_application_id", "decisions", ["application_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="uploaded"),
        sa.Column("quality_flags", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_application_id", "documents", ["application_id"])

    op.create_table(
        "document_extractions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(255), nullable=False),
        sa.Column("field_value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_extractions_document_id", "document_extractions", ["document_id"]
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=True),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("user_role", sa.String(50), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=True),
        sa.Column("decision_id", sa.Integer(), nullable=True),
        sa.Column("event_data", sa.Text(), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_application_id", "audit_events", ["application_id"])

    op.create_table(
        "demo_data_manifest",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("seeded_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("demo_data_manifest")
    op.drop_table("audit_events")
    op.drop_table("document_extractions")
    op.drop_table("documents")
    op.drop_table("decisions")
    op.drop_table("conditions")
    op.drop_table("rate_locks")
    op.drop_table("application_financials")
    op.drop_table("applications")
    op.drop_table("borrowers")
