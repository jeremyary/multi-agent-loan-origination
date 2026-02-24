# This project was developed with assistance from AI tools.
"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .admin import setup_admin
from .core.config import settings
from .inference.safety import log_safety_status
from .observability import log_observability_status
from .routes import admin, applications, chat, documents, health, hmda, public


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application startup/shutdown lifecycle."""
    log_safety_status()
    log_observability_status()
    from .services.conversation import get_conversation_service

    conversation_service = get_conversation_service()
    await conversation_service.initialize(settings.DATABASE_URL)
    yield
    await conversation_service.shutdown()


app = FastAPI(
    title="Summit Cap Financial API",
    description="Multi-agent loan origination system for Summit Cap Financial",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(public.router, prefix="/api/public", tags=["public"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(hmda.router, prefix="/api/hmda", tags=["hmda"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# Setup SQLAdmin dashboard at /admin
setup_admin(app)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {"message": "Welcome to Summit Cap Financial API"}
