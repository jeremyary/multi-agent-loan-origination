# This project was developed with assistance from AI tools.
"""
Application configuration.

All settings read from environment variables with sensible local dev defaults.
Group related settings together; each group becomes a section future PRs extend.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings -- single source of truth for env-driven config."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- App --
    APP_NAME: str = "summit-cap"
    DEBUG: bool = False

    # -- CORS --
    ALLOWED_HOSTS: list[str] = ["http://localhost:5173"]

    # -- Database --
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5433/summit-cap",
        description="Async SQLAlchemy connection string (asyncpg driver).",
    )

    # -- Auth (PR 4) --
    AUTH_DISABLED: bool = Field(
        default=False,
        description="Bypass JWT validation. Set True for tests and local dev without Keycloak.",
    )


settings = Settings()
