from fastapi import APIRouter
import os

router = APIRouter(prefix="/api", tags=["System"])


@router.get("/health", summary="Health Check")
async def health_check():
    """Health check endpoint to verify backend service operational status."""
    return {
        "status": "healthy",
        "application": os.getenv("APP_NAME", "NEGOZA")
    }
