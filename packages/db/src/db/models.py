# This project was developed with assistance from AI tools.
"""
Summit Cap Financial -- domain models

Mortgage lending lifecycle models covering applications, borrowers,
documents, underwriting conditions/decisions, and audit trail.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from .database import Base
from .enums import (
    ApplicationStage,
    ConditionSeverity,
    ConditionStatus,
    DecisionType,
    DocumentStatus,
    DocumentType,
    LoanType,
    UserRole,
)

class Borrower(Base):
    """Borrower profile linked to Keycloak identity."""

    __tablename__ = "borrowers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keycloak_user_id = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    ssn_encrypted = Column(String(255), nullable=True)
    dob = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    applications = relationship(
        "Application", back_populates="borrower", cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Borrower(id={self.id}, name='{self.first_name} {self.last_name}')>"


class Application(Base):
    """Mortgage loan application."""

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    borrower_id = Column(
        Integer, ForeignKey("borrowers.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    stage = Column(
        Enum(ApplicationStage, name="application_stage", native_enum=False),
        nullable=False,
        default=ApplicationStage.INQUIRY,
    )
    loan_type = Column(
        Enum(LoanType, name="loan_type", native_enum=False),
        nullable=True,
    )
    property_address = Column(Text, nullable=True)
    loan_amount = Column(Numeric(12, 2), nullable=True)
    property_value = Column(Numeric(12, 2), nullable=True)
    assigned_to = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    borrower = relationship("Borrower", back_populates="applications")
    financials = relationship(
        "ApplicationFinancials", back_populates="application",
        uselist=False, cascade="all, delete-orphan",
    )
    rate_locks = relationship(
        "RateLock", back_populates="application", cascade="all, delete-orphan",
    )
    conditions = relationship(
        "Condition", back_populates="application", cascade="all, delete-orphan",
    )
    decisions = relationship(
        "Decision", back_populates="application", cascade="all, delete-orphan",
    )
    documents = relationship(
        "Document", back_populates="application", cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Application(id={self.id}, stage='{self.stage}')>"


class ApplicationFinancials(Base):
    """Financial details for an application."""

    __tablename__ = "application_financials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    gross_monthly_income = Column(Numeric(12, 2), nullable=True)
    monthly_debts = Column(Numeric(12, 2), nullable=True)
    total_assets = Column(Numeric(14, 2), nullable=True)
    credit_score = Column(Integer, nullable=True)
    dti_ratio = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    application = relationship("Application", back_populates="financials")

    def __repr__(self):
        return f"<ApplicationFinancials(app_id={self.application_id}, credit={self.credit_score})>"


class RateLock(Base):
    """Rate lock on an application."""

    __tablename__ = "rate_locks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    locked_rate = Column(Float, nullable=False)
    lock_date = Column(DateTime(timezone=True), nullable=False)
    expiration_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    application = relationship("Application", back_populates="rate_locks")

    def __repr__(self):
        return f"<RateLock(app_id={self.application_id}, rate={self.locked_rate})>"


class Condition(Base):
    """Underwriting condition on an application."""

    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    description = Column(Text, nullable=False)
    severity = Column(
        Enum(ConditionSeverity, name="condition_severity", native_enum=False),
        nullable=False,
    )
    status = Column(
        Enum(ConditionStatus, name="condition_status", native_enum=False),
        nullable=False,
        default=ConditionStatus.OPEN,
    )
    issued_by = Column(String(255), nullable=True)
    cleared_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    application = relationship("Application", back_populates="conditions")

    def __repr__(self):
        return f"<Condition(id={self.id}, status='{self.status}')>"


class Decision(Base):
    """Underwriting decision on an application."""

    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    decision_type = Column(
        Enum(DecisionType, name="decision_type", native_enum=False),
        nullable=False,
    )
    rationale = Column(Text, nullable=True)
    ai_recommendation = Column(Text, nullable=True)
    decided_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    application = relationship("Application", back_populates="decisions")

    def __repr__(self):
        return f"<Decision(id={self.id}, type='{self.decision_type}')>"


class Document(Base):
    """Document uploaded for an application."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    doc_type = Column(
        Enum(DocumentType, name="document_type", native_enum=False),
        nullable=False,
    )
    file_path = Column(String(500), nullable=True)
    status = Column(
        Enum(DocumentStatus, name="document_status", native_enum=False),
        nullable=False,
        default=DocumentStatus.UPLOADED,
    )
    quality_flags = Column(Text, nullable=True)
    uploaded_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    application = relationship("Application", back_populates="documents")
    extractions = relationship(
        "DocumentExtraction", back_populates="document", cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Document(id={self.id}, type='{self.doc_type}')>"


class DocumentExtraction(Base):
    """Extracted field from a document."""

    __tablename__ = "document_extractions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    field_name = Column(String(255), nullable=False)
    field_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    source_page = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("Document", back_populates="extractions")

    def __repr__(self):
        return f"<DocumentExtraction(doc_id={self.document_id}, field='{self.field_name}')>"


class AuditEvent(Base):
    """Append-only audit trail. INSERT + SELECT only -- no UPDATE or DELETE."""

    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    prev_hash = Column(String(64), nullable=True)
    user_id = Column(String(255), nullable=True)
    user_role = Column(String(50), nullable=True)
    event_type = Column(String(100), nullable=False, index=True)
    application_id = Column(Integer, nullable=True, index=True)
    decision_id = Column(Integer, nullable=True)
    event_data = Column(Text, nullable=True)
    session_id = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<AuditEvent(id={self.id}, type='{self.event_type}')>"


class DemoDataManifest(Base):
    """Tracks demo data seeding for idempotency."""

    __tablename__ = "demo_data_manifest"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seeded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    config_hash = Column(String(64), nullable=False)
    summary = Column(Text, nullable=True)

    def __repr__(self):
        return f"<DemoDataManifest(id={self.id}, seeded_at='{self.seeded_at}')>"


class HmdaDemographic(Base):
    """HMDA demographic data -- isolated in hmda schema."""

    __tablename__ = "demographics"
    __table_args__ = {"schema": "hmda"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, nullable=False, index=True)
    race = Column(String(100), nullable=True)
    ethnicity = Column(String(100), nullable=True)
    sex = Column(String(50), nullable=True)
    age = Column(String(20), nullable=True)
    collection_method = Column(String(50), nullable=False, default="self_reported")
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<HmdaDemographic(id={self.id}, app_id={self.application_id})>"


class HmdaLoanData(Base):
    """Non-demographic HMDA-reportable loan data -- snapshot at underwriting submission."""

    __tablename__ = "loan_data"
    __table_args__ = {"schema": "hmda"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, nullable=False, unique=True, index=True)
    gross_monthly_income = Column(Numeric(12, 2), nullable=True)
    dti_ratio = Column(Float, nullable=True)
    credit_score = Column(Integer, nullable=True)
    loan_type = Column(String(50), nullable=True)
    loan_purpose = Column(String(50), nullable=True)
    property_location = Column(Text, nullable=True)
    interest_rate = Column(Float, nullable=True)
    total_fees = Column(Numeric(10, 2), nullable=True)
    snapshot_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<HmdaLoanData(id={self.id}, app_id={self.application_id})>"
