"""
Application configuration
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Basic settings
    APP_NAME: str = "summit-cap"
    DEBUG: bool = False
    
    # CORS settings
    ALLOWED_HOSTS: list[str] = ["http://localhost:5173"]
    
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5433/summit-cap"
    
    class Config:
        env_file = ".env"


settings = Settings()
