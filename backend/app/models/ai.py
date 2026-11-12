from typing import Optional
from pydantic import BaseModel, Field


class AITestRequest(BaseModel):
    """Request payload for POST /api/ai/test."""
    message: str = Field(
        ...,
        description="Prompt or query message to send to the Gemini model",
        examples=["Try to get this smartwatch for 7500 including delivery"],
    )


class AITestResponse(BaseModel):
    """Response payload for POST /api/ai/test."""
    status: str = Field(default="success", description="Response status indicator")
    model: str = Field(..., description="The Gemini model utilized")
    message: str = Field(..., description="The original prompt message received")
    response: str = Field(..., description="Actual response text returned from the Gemini model")
    error: Optional[str] = Field(default=None, description="Optional error message if any")
