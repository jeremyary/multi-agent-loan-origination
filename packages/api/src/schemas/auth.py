# This project was developed with assistance from AI tools.
"""Authentication and authorization schemas."""

from db.enums import UserRole
from pydantic import BaseModel, ConfigDict, Field


class DataScope(BaseModel):
    """Data visibility rules injected by RBAC middleware."""

    assigned_to: str | None = None
    pii_mask: bool = False
    own_data_only: bool = False
    user_id: str | None = None
    full_pipeline: bool = False


class UserContext(BaseModel):
    """Injected by auth middleware into every authenticated request."""

    model_config = ConfigDict(frozen=True)

    user_id: str
    role: UserRole
    email: str
    name: str
    data_scope: DataScope = Field(default_factory=DataScope)


class TokenPayload(BaseModel):
    """Decoded JWT token claims from Keycloak."""

    sub: str
    email: str = ""
    preferred_username: str = ""
    name: str = ""
    realm_access: dict = Field(default_factory=dict)
