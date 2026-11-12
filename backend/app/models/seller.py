from typing import List, Optional, Literal, Any, Dict
from pydantic import BaseModel, Field, model_validator


class MerchantCommercialProfile(BaseModel):
    """
    Structured commercial boundaries and policies configured by the merchant.
    Gemini is never allowed to override or invent these values.
    """
    merchant_id: str = Field(..., description="Unique merchant identifier", examples=["merchant-chronos"])
    merchant_name: str = Field(..., description="Display name of the merchant", examples=["Chronos Official"])
    product_id: str = Field(..., description="Product identifier", examples=["prod-1"])
    listed_price: float = Field(..., gt=0, description="Standard public advertised list price", examples=[299.0])
    minimum_acceptable_price: float = Field(..., gt=0, description="Strict minimum price floor merchant will accept", examples=[235.0])
    preferred_price: Optional[float] = Field(default=None, gt=0, description="Merchant target selling price protecting margin", examples=[270.0])
    available_inventory: int = Field(default=10, ge=0, description="Current available inventory units", examples=[15])
    maximum_permitted_discount: float = Field(..., ge=0, description="Maximum discount amount below list price allowed", examples=[65.0])
    delivery_cost: float = Field(default=0.0, ge=0, description="Standard merchant shipping cost", examples=[15.0])
    free_delivery_allowed: bool = Field(default=True, description="Whether merchant policy permits absorbing delivery cost", examples=[True])
    promotional_rules: List[str] = Field(default_factory=list, description="Commercial conditions and promotional policies")

    @model_validator(mode="after")
    def validate_pricing_bounds(self) -> "MerchantCommercialProfile":
        """
        Guarantees mathematical integrity of merchant pricing constraints:
        minimum_acceptable_price <= preferred_price <= listed_price.
        """
        self.listed_price = round(self.listed_price, 2)
        if self.minimum_acceptable_price > self.listed_price:
            self.minimum_acceptable_price = round(self.listed_price * 0.80, 2)
        else:
            self.minimum_acceptable_price = round(self.minimum_acceptable_price, 2)

        max_possible_discount = round(self.listed_price - self.minimum_acceptable_price, 2)
        if self.maximum_permitted_discount > max_possible_discount:
            self.maximum_permitted_discount = max_possible_discount
        else:
            self.maximum_permitted_discount = round(self.maximum_permitted_discount, 2)

        # Calibrate and bound preferred_price
        if self.preferred_price is None or self.preferred_price <= 0:
            # Default preferred price: targets ~70% of the margin between floor and list price
            self.preferred_price = round(
                self.minimum_acceptable_price + (self.listed_price - self.minimum_acceptable_price) * 0.70, 2
            )
        else:
            self.preferred_price = round(
                max(self.minimum_acceptable_price, min(self.listed_price, self.preferred_price)), 2
            )

        return self


class SellerRespondRequest(BaseModel):
    """
    Request model for the Buyer Agent to submit a purchase/negotiation proposal to the Seller Agent.
    """
    product_id: str = Field(..., description="Product identifier", examples=["prod-1"])
    product_name: Optional[str] = Field(default="Product", description="Display name of the product", examples=["Aura Horizon Chrono Pro"])
    merchant_id: Optional[str] = Field(default=None, description="Optional merchant identifier")
    merchant_name: Optional[str] = Field(default=None, description="Optional merchant display name")
    buyer_proposed_price: float = Field(..., gt=0, description="Price proposed by Buyer Agent", examples=[240.0])
    delivery_conditions: Optional[str] = Field(default="Free standard delivery", description="Delivery terms requested by Buyer Agent")
    merchant_constraints: Optional[MerchantCommercialProfile] = Field(
        default=None,
        description="Optional custom merchant commercial constraints. If omitted, simulated merchant profile is loaded."
    )
    previous_context: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional history of preceding negotiation offers or messages"
    )
    round_number: Optional[int] = Field(
        default=1,
        description="Current negotiation round number"
    )


class SellerRespondResponse(BaseModel):
    """
    Structured decision and counterproposal returned by the NEGOZA Seller Agent.
    Strictly validated and enforced by deterministic Python logic.
    """
    status: Literal["accepted", "counter_offer", "rejected"] = Field(
        ...,
        description="Negotiation decision status: accepted, counter_offer, or rejected"
    )
    agent: str = Field(default="seller", description="Agent identifier")
    offered_price: Optional[float] = Field(
        default=None,
        description="Price offered by the seller. Must be >= merchant minimum acceptable price if status is accepted or counter_offer."
    )
    delivery: str = Field(
        ...,
        description="Delivery terms agreed or counter-offered (e.g. 'free', 'paid', or specific shipping conditions)"
    )
    reasoning: str = Field(
        ...,
        description="Commercial rationale evaluated against merchant constraints"
    )
    conditions: List[str] = Field(
        default_factory=list,
        description="Commercial conditions, promotional terms, or non-negotiable clauses"
    )
    message: str = Field(
        ...,
        description="Human-readable response message directed to the Buyer Agent"
    )
