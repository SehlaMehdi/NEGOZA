"""Browser Models - Pydantic schemas for KERNEL Cloud Browser automation."""

from typing import Optional
from pydantic import BaseModel, Field


class BrowserStartRequest(BaseModel):
    """Request payload to initiate a KERNEL cloud browser session."""
    merchant_url: str = Field(
        ...,
        description="Public URL for the browser session to navigate to (e.g. 'https://example.com')",
        example="https://example.com"
    )
    timeout_seconds: Optional[int] = Field(
        300,
        description="Inactivity timeout in seconds before auto-termination (min 10, max 259200)",
        ge=10,
        le=259200
    )


class BrowserStartResponse(BaseModel):
    """Response returned upon successful creation of a KERNEL cloud browser session."""
    session_id: str = Field(..., description="Unique KERNEL browser session identifier")
    merchant_url: str = Field(..., description="Target URL navigated to by the browser")
    live_view_url: Optional[str] = Field(None, description="Interactive live browser view URL for real-time monitoring")
    status: str = Field("active", description="Current session status ('active', 'closed')")
    created_at: Optional[str] = Field(None, description="ISO timestamp when browser was spun up")
    message: str = Field(..., description="Summary status message")


class BrowserInspectRequest(BaseModel):
    """Request payload to inspect the active DOM/page of a KERNEL cloud browser."""
    session_id: str = Field(..., description="Session ID of the active KERNEL browser session")


class BrowserInspectResponse(BaseModel):
    """Response containing inspected page content and metadata."""
    session_id: str = Field(..., description="Unique KERNEL browser session identifier")
    title: Optional[str] = Field(None, description="Current page title")
    url: Optional[str] = Field(None, description="Current browser URL")
    content_preview: Optional[str] = Field(None, description="Trimmed text content extract from the page body")
    live_view_url: Optional[str] = Field(None, description="Live browser view URL for observability")
    success: bool = Field(True, description="Whether the inspection execution succeeded")
    message: str = Field(..., description="Summary message")


class BrowserCloseRequest(BaseModel):
    """Request payload to close and clean up a KERNEL cloud browser session."""
    session_id: str = Field(..., description="Session ID of the KERNEL browser session to terminate")


class BrowserCloseResponse(BaseModel):
    """Response confirming termination of a KERNEL cloud browser session."""
    session_id: str = Field(..., description="Unique KERNEL browser session identifier")
    status: str = Field("closed", description="Session state confirming termination ('closed')")
    message: str = Field(..., description="Confirmation message")
