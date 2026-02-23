"""
FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .admin import setup_admin
from .core.config import settings
from .routes import health, public

app = FastAPI(
    title="Summit Cap Financial API",
    description="Multi-agent loan origination system for Summit Cap Financial",
    version="0.1.0",
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

# Setup SQLAdmin dashboard at /admin
setup_admin(app)

@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {"message": "Welcome to Summit Cap Financial API"}
