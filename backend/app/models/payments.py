"""Payment Models - Pydantic schemas for payment integrations."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class PayPalStatusResponse(BaseModel):
    """Response schema for PayPal Sandbox authentication verification."""
    status: str = Field(..., description="Authentication status ('authenticated', 'failed', 'unconfigured')")
    authenticated: bool = Field(..., description="Whether Sandbox OAuth 2.0 authentication succeeded")
    environment: str = Field("sandbox", description="PayPal environment ('sandbox' or 'live')")
    base_url: str = Field(..., description="PayPal REST API base URL")
    app_id: Optional[str] = Field(None, description="PayPal Application ID returned by OAuth")
    token_type: Optional[str] = Field(None, description="Token type (e.g. 'Bearer')")
    expires_in: Optional[int] = Field(None, description="Token validity duration in seconds")
    message: str = Field(..., description="Human-readable status summary")


class PayPalCreateOrderRequest(BaseModel):
    """Request schema for creating a PayPal checkout order for an agreed deal."""
    negotiation_id: str = Field(..., description="ID or reference of the negotiated deal")
    product_name: str = Field(..., description="Product title being purchased")
    amount: float = Field(..., gt=0, description="Total payable amount negotiated by agents")
    currency: str = Field("USD", description="Currency code (USD)")


class PayPalCreateOrderResponse(BaseModel):
    """Response schema for a newly created PayPal Sandbox order."""
    order_id: str = Field(..., description="PayPal Sandbox order ID")
    status: str = Field(..., description="Order lifecycle status (e.g. 'CREATED')")
    amount: float = Field(..., description="Order amount")
    currency: str = Field("USD", description="Currency code")
    approve_url: Optional[str] = Field(None, description="URL for buyer approval in PayPal Sandbox")
    environment: str = Field("sandbox", description="PayPal environment ('sandbox')")
    message: str = Field(..., description="Status summary message")


class PayPalCaptureOrderResponse(BaseModel):
    """Response schema for capturing a PayPal Sandbox order."""
    order_id: str = Field(..., description="PayPal Sandbox order ID")
    status: str = Field(..., description="Capture status ('COMPLETED', 'ORDER_NOT_APPROVED', 'FAILED')")
    capture_id: Optional[str] = Field(None, description="PayPal capture transaction ID if completed")
    amount: Optional[float] = Field(None, description="Captured amount")
    currency: Optional[str] = Field(None, description="Captured currency")
    payer_email: Optional[str] = Field(None, description="Payer email if available")
    message: str = Field(..., description="Detailed capture outcome message")
    raw_details: Optional[Dict[str, Any]] = Field(None, description="Raw details from PayPal REST API")
