# This project was developed with assistance from AI tools.
"""Shared test factory functions for creating mock objects.

Extracts common mock creation patterns from test files to eliminate duplication
and ensure consistency across test suites.
"""

from unittest.mock import MagicMock


def make_mock_condition(
    id=1,
    description="Verify employment",
    severity="prior_to_approval",
    status="open",
    response_text=None,
    issued_by="maria-uuid",
    application_id=100,
    cleared_by=None,
    due_date=None,
    iteration_count=0,
    waiver_rationale=None,
):
    """Create a mock Condition ORM object.

    Args:
        id: Condition ID.
        description: Condition description text.
        severity: Severity level (prior_to_approval, prior_to_docs, etc.).
        status: Condition status (open, responded, etc.).
        response_text: Borrower's response text.
        issued_by: User ID who issued the condition.
        application_id: Associated application ID.
        cleared_by: User ID who cleared the condition.
        due_date: Due date for the condition.
        iteration_count: Number of times returned to borrower.
        waiver_rationale: Rationale for waiving condition.

    Returns:
        MagicMock configured as a Condition model instance.
    """
    from db.enums import ConditionSeverity, ConditionStatus

    c = MagicMock()
    c.id = id
    c.description = description
    c.severity = ConditionSeverity(severity)
    c.status = ConditionStatus(status)
    c.response_text = response_text
    c.issued_by = issued_by
    c.cleared_by = cleared_by
    c.due_date = due_date
    c.iteration_count = iteration_count
    c.waiver_rationale = waiver_rationale
    c.application_id = application_id
    c.created_at = MagicMock()
    c.created_at.isoformat.return_value = "2026-02-20T00:00:00+00:00"
    return c


def make_mock_app(stage="underwriting", id=100):
    """Create a mock Application ORM object.

    Args:
        stage: Application stage enum value.
        id: Application ID.

    Returns:
        MagicMock configured as an Application model instance with loan details.
    """
    from decimal import Decimal

    from db.enums import ApplicationStage, LoanType

    app = MagicMock()
    app.stage = ApplicationStage(stage)
    app.id = id
    app.loan_amount = Decimal("350000")
    app.property_value = Decimal("450000")
    app.loan_type = LoanType.CONVENTIONAL_30
    app.property_address = "123 Main St, Denver, CO"
    app.le_delivery_date = None
    app.cd_delivery_date = None
    app.application_borrowers = []
    return app


def make_uw_user():
    """Create a mock underwriter UserContext.

    Returns:
        MagicMock configured as a UserContext for an underwriter.
    """
    user = MagicMock()
    user.user_id = "uw-maria"
    user.role = MagicMock()
    user.role.value = "underwriter"
    user.data_scope = MagicMock()
    return user


def make_mock_decision(
    id=1,
    application_id=100,
    decision_type="approved",
    rationale="Strong profile",
    ai_recommendation=None,
    ai_agreement=None,
    denial_reasons=None,
    credit_score_used=None,
    credit_score_source=None,
    contributing_factors=None,
):
    """Create a mock Decision ORM object.

    Args:
        id: Decision ID.
        application_id: Associated application ID.
        decision_type: Decision type (approved, denied, etc.).
        rationale: Underwriter's rationale.
        ai_recommendation: AI's recommendation text.
        ai_agreement: Whether UW and AI agreed.
        denial_reasons: List of denial reasons (for DENIED decisions).
        credit_score_used: Credit score used in decision.
        credit_score_source: Credit bureau source.
        contributing_factors: Additional factors considered.

    Returns:
        MagicMock configured as a Decision model instance.
    """
    from db.enums import DecisionType

    d = MagicMock()
    d.id = id
    d.application_id = application_id
    d.decision_type = DecisionType(decision_type)
    d.rationale = rationale
    d.ai_recommendation = ai_recommendation
    d.ai_agreement = ai_agreement
    d.override_rationale = None
    d.denial_reasons = denial_reasons
    d.credit_score_used = credit_score_used
    d.credit_score_source = credit_score_source
    d.contributing_factors = contributing_factors
    d.decided_by = "uw-maria"
    d.created_at = MagicMock()
    d.created_at.isoformat.return_value = "2026-02-27T12:00:00+00:00"
    return d
