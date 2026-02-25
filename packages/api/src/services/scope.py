# This project was developed with assistance from AI tools.
"""Shared data scope filtering for service queries.

Centralizes the DataScope -> SQL WHERE logic so that each resource service
applies the same rules. The join_to_application parameter handles the
different join paths needed for Application queries vs. child-entity
queries (Documents, Conditions, etc.).
"""

from db import Application, ApplicationBorrower, Borrower

from ..schemas.auth import DataScope, UserContext


def apply_data_scope(stmt, scope: DataScope, user: UserContext, *, join_to_application=None):
    """Apply data scope filtering to a SQLAlchemy query.

    Args:
        stmt: A SQLAlchemy select statement.
        scope: The caller's DataScope.
        user: The caller's UserContext.
        join_to_application: ORM relationship attribute to join to reach
            Application (e.g., ``Document.application``). Pass ``None``
            when querying Application directly.

    Returns:
        The filtered statement.
    """
    if scope.own_data_only and scope.user_id:
        if join_to_application is not None:
            stmt = stmt.join(join_to_application)
        stmt = (
            stmt.join(
                ApplicationBorrower,
                ApplicationBorrower.application_id == Application.id,
            )
            .join(
                Borrower,
                Borrower.id == ApplicationBorrower.borrower_id,
            )
            .where(
                Borrower.keycloak_user_id == scope.user_id,
            )
        )
    elif scope.assigned_to:
        if join_to_application is not None:
            stmt = stmt.join(join_to_application)
        stmt = stmt.where(Application.assigned_to == scope.assigned_to)
    return stmt
