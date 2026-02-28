# This project was developed with assistance from AI tools.
"""Unit tests for data scope construction (core.auth.build_data_scope).

Tests that different roles get correct data scopes: borrower sees own data,
loan officer sees assigned applications, underwriter/admin see all.
"""

from db.enums import UserRole

from src.core.auth import build_data_scope


def test_borrower_scope_own_data_only():
    """Borrowers get own_data_only=True with their user_id."""
    scope = build_data_scope(UserRole.BORROWER, "borrower-123")
    assert scope.own_data_only is True
    assert scope.user_id == "borrower-123"
    assert scope.assigned_to is None
    assert scope.pii_mask is False
    assert scope.full_pipeline is False


def test_loan_officer_scope_assigned():
    """Loan officers get assigned_to=user_id."""
    scope = build_data_scope(UserRole.LOAN_OFFICER, "lo-456")
    assert scope.assigned_to == "lo-456"
    assert scope.own_data_only is False
    assert scope.pii_mask is False
    assert scope.full_pipeline is False


def test_underwriter_scope_full_pipeline():
    """Underwriters get full_pipeline=True."""
    scope = build_data_scope(UserRole.UNDERWRITER, "uw-789")
    assert scope.full_pipeline is True
    assert scope.pii_mask is False
    assert scope.own_data_only is False
    assert scope.assigned_to is None


def test_admin_scope_full_pipeline():
    """Admins get full_pipeline=True."""
    scope = build_data_scope(UserRole.ADMIN, "admin-123")
    assert scope.full_pipeline is True
    assert scope.pii_mask is False
    assert scope.own_data_only is False


def test_ceo_scope_pii_masked():
    """CEOs get pii_mask=True and document_metadata_only=True."""
    scope = build_data_scope(UserRole.CEO, "ceo-999")
    assert scope.pii_mask is True
    assert scope.document_metadata_only is True
    assert scope.full_pipeline is True
    assert scope.own_data_only is False


def test_unknown_role_minimal_access():
    """Unknown roles get minimal access (all flags False)."""
    # Prospect is a valid role but gets minimal scope
    scope = build_data_scope(UserRole.PROSPECT, "prospect-000")
    assert scope.own_data_only is False
    assert scope.assigned_to is None
    assert scope.pii_mask is False
    assert scope.full_pipeline is False
    assert scope.document_metadata_only is False
