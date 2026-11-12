import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file before importing routers and services
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
if not env_path.exists():
    env_path = BASE_DIR / ".env.example"
load_dotenv(dotenv_path=env_path, override=True)

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routes.health import router as health_router
from app.routes.ai import router as ai_router
from app.routes.agents import router as agents_router
from app.routes.negotiation import router as negotiation_router
from app.routes.payments import router as payments_router
from app.routes.browser import router as browser_router
from app.routes.products import router as products_router

# App Configuration
APP_NAME = os.getenv("APP_NAME", "NEGOZA")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

# FastAPI Application Factory
app = FastAPI(
    title=f"{APP_NAME} API",
    description="Backend API for NEGOZA — Autonomous Agentic Commerce Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware Configuration
cors_origins_env = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"
)
origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health_router)
app.include_router(ai_router)
app.include_router(agents_router)
app.include_router(negotiation_router)
app.include_router(payments_router)
app.include_router(browser_router)
app.include_router(products_router)


# Root Endpoint
@app.get("/", summary="Root Welcome")
async def root():
    """Root endpoint welcoming clients to NEGOZA API."""
    return {
        "message": f"Welcome to {APP_NAME} Agentic Commerce API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
        "ai_test": "/api/ai/test",
        "buyer_agent": "/api/agents/buyer/prepare",
        "seller_agent": "/api/agents/seller/respond",
        "negotiation": "/api/negotiation/start",
        "paypal_status": "/api/payments/paypal/status",
        "browser_start": "/api/browser/start",
        "browser_inspect": "/api/browser/inspect",
        "browser_close": "/api/browser/close",
        "product_search": "/api/products/search"
    }


# HTTP Exception Handler (Preserves correct 4xx and 5xx status codes)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# Global Exception Handler (Fallback for unhandled crashes)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Fallback exception handler for unhandled errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred processing your request.",
            "detail": str(exc) if DEBUG else None
        }
    )
