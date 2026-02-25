# This project was developed with assistance from AI tools.
"""
Domain enums for the mortgage lending lifecycle.

Shared domain types used by both SQLAlchemy models (db package)
and Pydantic schemas (api package).
"""

import enum


class ApplicationStage(str, enum.Enum):
    INQUIRY = "inquiry"
    PREQUALIFICATION = "prequalification"
    APPLICATION = "application"
    PROCESSING = "processing"
    UNDERWRITING = "underwriting"
    CONDITIONAL_APPROVAL = "conditional_approval"
    CLEAR_TO_CLOSE = "clear_to_close"
    CLOSED = "closed"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PROSPECT = "prospect"
    BORROWER = "borrower"
    LOAN_OFFICER = "loan_officer"
    UNDERWRITER = "underwriter"
    CEO = "ceo"


class LoanType(str, enum.Enum):
    CONVENTIONAL_30 = "conventional_30"
    CONVENTIONAL_15 = "conventional_15"
    FHA = "fha"
    VA = "va"
    JUMBO = "jumbo"
    USDA = "usda"


class DocumentType(str, enum.Enum):
    W2 = "w2"
    PAY_STUB = "pay_stub"
    TAX_RETURN = "tax_return"
    BANK_STATEMENT = "bank_statement"
    ID = "id"
    PROPERTY_APPRAISAL = "property_appraisal"
    INSURANCE = "insurance"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSING_COMPLETE = "processing_complete"
    PROCESSING_FAILED = "processing_failed"
    PENDING_REVIEW = "pending_review"
    ACCEPTED = "accepted"
    FLAGGED_FOR_RESUBMISSION = "flagged_for_resubmission"
    REJECTED = "rejected"


class ConditionSeverity(str, enum.Enum):
    PRIOR_TO_APPROVAL = "prior_to_approval"
    PRIOR_TO_DOCS = "prior_to_docs"
    PRIOR_TO_CLOSING = "prior_to_closing"
    PRIOR_TO_FUNDING = "prior_to_funding"


class ConditionStatus(str, enum.Enum):
    OPEN = "open"
    RESPONDED = "responded"
    UNDER_REVIEW = "under_review"
    CLEARED = "cleared"
    WAIVED = "waived"
    ESCALATED = "escalated"


class DecisionType(str, enum.Enum):
    APPROVED = "approved"
    CONDITIONAL_APPROVAL = "conditional_approval"
    SUSPENDED = "suspended"
    DENIED = "denied"
