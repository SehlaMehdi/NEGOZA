import os
from fastapi import APIRouter, HTTPException, status
from app.models.ai import AITestRequest, AITestResponse
from app.services.gemini_service import gemini_service

router = APIRouter(prefix="/api/ai", tags=["AI Engine"])


@router.post(
    "/test",
    response_model=AITestResponse,
    summary="Test Gemini AI Integration",
    description="Sends a test prompt message to Google Gemini and returns the generated AI response.",
)
async def test_gemini_ai(payload: AITestRequest):
    """
    Receives a test message prompt, delegates it asynchronously to the Gemini service,
    and returns Gemini's actual response.
    """
    clean_message = payload.message.strip() if payload.message else ""
    if not clean_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty. Please provide a non-empty message string.",
        )

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    try:
        generated_text = await gemini_service.generate_response(clean_message, model=model_name)
        return AITestResponse(
            status="success",
            model=model_name,
            message=clean_message,
            response=generated_text,
        )

    except ValueError as val_err:
        # Handles missing or unconfigured GEMINI_API_KEY
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(val_err),
        ) from val_err

    except PermissionError as perm_err:
        # Handles invalid or unauthorized GEMINI_API_KEY
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(perm_err),
        ) from perm_err

    except RuntimeError as run_err:
        # Handles upstream Gemini API quota / rate limits / service errors
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err),
        ) from run_err

    except Exception as exc:
        # Generic fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while communicating with Gemini: {str(exc)}",
        ) from exc
