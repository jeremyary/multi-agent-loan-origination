# This project was developed with assistance from AI tools.
__version__ = "0.1.0"

from .database import Base, DatabaseService, get_db, get_db_service
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
from .models import (
    Application,
    ApplicationFinancials,
    AuditEvent,
    Borrower,
    Condition,
    Decision,
    DemoDataManifest,
    Document,
    DocumentExtraction,
    RateLock,
)

__all__ = [
    "Base",
    "DatabaseService",
    "get_db",
    "get_db_service",
    "__version__",
    # Enums
    "ApplicationStage",
    "UserRole",
    "LoanType",
    "DocumentType",
    "DocumentStatus",
    "ConditionSeverity",
    "ConditionStatus",
    "DecisionType",
    # Models
    "Application",
    "ApplicationFinancials",
    "AuditEvent",
    "Borrower",
    "Condition",
    "Decision",
    "DemoDataManifest",
    "Document",
    "DocumentExtraction",
    "RateLock",
]
