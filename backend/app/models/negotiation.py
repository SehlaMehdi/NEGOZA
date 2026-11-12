from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, model_validator
from app.models.seller import MerchantCommercialProfile


class NegotiationRoundRecord(BaseModel):
    """
    Detailed transcript record for a single round / action in an agent-to-agent negotiation.
    """
    round_number: int = Field(..., description="Round sequence number (1 to 5)")
    agent: Literal["buyer", "seller"] = Field(..., description="Agent who submitted this proposal or response")
    action: Literal["opening_offer", "counter_offer", "accepted", "rejected"] = Field(
        ...,
        description="Action type taken by the agent"
    )
    proposed_price: Optional[float] = Field(
        default=None,
        description="Price proposed or agreed upon in this turn (null if outright rejection)"
    )
    delivery_conditions: str = Field(..., description="Delivery terms proposed or agreed upon")
    agent_response: str = Field(..., description="Human-readable message or dialogue from the agent")
    reasoning: str = Field(..., description="Strategic or commercial reasoning justifying this action")
    round_status: str = Field(
        ...,
        description="Status of this negotiation turn (e.g. in_progress, counter_offered, deal_reached, rejected)"
    )


class NegotiationStartRequest(BaseModel):
    """
    Request payload to initiate an autonomous Agent-to-Agent negotiation loop.
    """
    product_id: str = Field(..., description="Product identifier", examples=["prod-1"])
    product_name: str = Field(..., description="Display title of the product", examples=["Aura Horizon Chrono Pro"])
    merchant_id: Optional[str] = Field(default=None, description="Merchant identifier")
    merchant_name: Optional[str] = Field(default=None, description="Merchant display name")
    advertised_price: float = Field(..., gt=0, description="Advertised list price", examples=[299.0])
    target_price: float = Field(..., gt=0, description="Customer target price", examples=[240.0])
    max_price: Optional[float] = Field(
        default=None,
        gt=0,
        description="Customer maximum acceptable price ceiling (defaults to advertised price if not set)",
        examples=[260.0]
    )
    delivery_preference: Optional[str] = Field(
        default="Free standard delivery",
        description="Buyer's delivery requirement"
    )
    requirements: Optional[List[str]] = Field(
        default_factory=list,
        description="Optional customer constraints or requirements"
    )
    merchant_constraints: Optional[MerchantCommercialProfile] = Field(
        default=None,
        description="Optional custom merchant commercial constraints. If omitted, simulated merchant profile is used."
    )
    max_rounds: Optional[int] = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum negotiation rounds permitted (prototype limit is 5)"
    )

    @model_validator(mode="after")
    def validate_negotiation_parameters(self) -> "NegotiationStartRequest":
        if self.target_price > self.advertised_price:
            raise ValueError(f"Target price (${self.target_price}) cannot exceed advertised price (${self.advertised_price}).")
        
        if self.max_price is None:
            self.max_price = self.advertised_price
        elif self.max_price < self.target_price:
            raise ValueError(f"Maximum acceptable price (${self.max_price}) cannot be less than target price (${self.target_price}).")
        
        return self


class NegotiationStartResponse(BaseModel):
    """
    Complete outcome and auditable transcript returned after negotiation loop completes.
    """
    negotiation_id: str = Field(..., description="Unique negotiation session UUID")
    product_id: str = Field(..., description="Product identifier")
    product_name: str = Field(..., description="Product title")
    merchant_id: str = Field(..., description="Merchant identifier")
    merchant_name: str = Field(..., description="Merchant name")
    initial_advertised_price: float = Field(..., description="Starting list price before negotiation")
    target_price: float = Field(..., description="Buyer's target price")
    max_price: float = Field(..., description="Buyer's maximum acceptable ceiling price")
    final_agreed_price: Optional[float] = Field(
        default=None,
        description="Final agreed price if deal_reached, otherwise null"
    )
    delivery_terms: Optional[str] = Field(
        default=None,
        description="Final agreed delivery conditions"
    )
    rounds_count: int = Field(..., description="Total rounds conducted before termination")
    status: Literal["deal_reached", "negotiation_failed", "maximum_rounds_reached"] = Field(
        ...,
        description="Final negotiation status: deal_reached, negotiation_failed, or maximum_rounds_reached"
    )
    summary: str = Field(..., description="Short explanation of the outcome")
    transcript: List[NegotiationRoundRecord] = Field(
        default_factory=list,
        description="Step-by-step audit transcript of all proposals and agent responses"
    )
