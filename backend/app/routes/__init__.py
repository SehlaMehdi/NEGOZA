"""API Routes Package."""

from app.routes.health import router as health_router
from app.routes.ai import router as ai_router
from app.routes.agents import router as agents_router
from app.routes.negotiation import router as negotiation_router

__all__ = ["health_router", "ai_router", "agents_router", "negotiation_router"]
