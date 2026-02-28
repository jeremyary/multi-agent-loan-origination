# This project was developed with assistance from AI tools.
"""Pure auth utility functions with no FastAPI or HTTP dependencies.

These are used by both the middleware layer (HTTP request auth) and the
agent tool layer (LangGraph state auth).  Keeping them separate from
``middleware/auth.py`` avoids pulling FastAPI/Starlette imports into
agent code that runs outside the request lifecycle.
"""

from db.enums import UserRole

from ..schemas.auth import DataScope


def build_data_scope(role: UserRole, user_id: str) -> DataScope:
    """Build data scope rules based on the user's role."""
    if role == UserRole.BORROWER:
        return DataScope(own_data_only=True, user_id=user_id)
    if role == UserRole.LOAN_OFFICER:
        return DataScope(assigned_to=user_id)
    if role == UserRole.CEO:
        return DataScope(pii_mask=True, document_metadata_only=True, full_pipeline=True)
    if role == UserRole.UNDERWRITER:
        return DataScope(full_pipeline=True)
    if role == UserRole.ADMIN:
        return DataScope(full_pipeline=True)
    # prospect or unknown -- minimal access
    return DataScope()
