"""Product Models - Pydantic schemas for Channel3 product discovery and catalog retrieval."""

from typing import Optional, List
from pydantic import BaseModel, Field


class Channel3Offer(BaseModel):
    """Represents a specific merchant's offer for a product."""
    domain: Optional[str] = Field(None, description="Merchant retailer domain (e.g. 'bestbuy.com')")
    url: Optional[str] = Field(None, description="Direct checkout/product buy URL")
    price: Optional[float] = Field(None, description="Offered price in specified currency")
    compare_at_price: Optional[float] = Field(None, description="Original list or compare-at price")
    currency: str = Field("USD", description="Currency ISO code")
    availability: Optional[str] = Field(None, description="Stock status ('InStock', 'OutOfStock')")


class ProductItem(BaseModel):
    """
    Normalized product model for NEGOZA storefront and agent activation.
    Provides dual-compatibility for camelCase (frontend React) and snake_case.
    """
    id: str = Field(..., description="Unique product ID from Channel3")
    name: str = Field(..., description="Product title / name")
    description: Optional[str] = Field(None, description="Product description or key highlights")
    merchant: str = Field(..., description="Selling merchant or primary retailer domain")
    category: str = Field("Electronics", description="Product category classification")
    advertisedPrice: float = Field(..., description="Current advertised price for buyer agent")
    originalPrice: float = Field(..., description="Original list price / MSRP before discounts")
    suggestedBudget: Optional[float] = Field(None, description="Suggested initial negotiation budget")
    currency: str = Field("USD", description="Currency ISO code")
    image: str = Field(..., description="Primary high-resolution product image URL")
    productUrl: Optional[str] = Field(None, description="Direct merchant URL where product is sold")
    rating: Optional[float] = Field(None, description="Average user rating score out of 5.0")
    reviewsCount: Optional[int] = Field(None, description="Total number of reviews")
    brand: Optional[str] = Field(None, description="Brand manufacturer name")
    sponsored: bool = Field(True, description="Whether the product is featured in discover feed")
    offers: List[Channel3Offer] = Field(default_factory=list, description="All retailer offers available")

    # Snake_case compatibility attributes
    advertised_price: Optional[float] = None
    original_price: Optional[float] = None
    product_url: Optional[str] = None
    suggested_budget: Optional[float] = None

    def model_post_init(self, __context) -> None:
        """Keep snake_case and camelCase attributes synchronized."""
        if self.advertised_price is None:
            self.advertised_price = self.advertisedPrice
        if self.original_price is None:
            self.original_price = self.originalPrice
        if self.product_url is None:
            self.product_url = self.productUrl
        if self.suggested_budget is None:
            self.suggested_budget = self.suggestedBudget


class ProductSearchResponse(BaseModel):
    """Response envelope for product search queries."""
    query: str = Field(..., description="Original search keyword query")
    count: int = Field(..., description="Number of products returned")
    products: List[ProductItem] = Field(default_factory=list, description="List of discovered products")
    source: str = Field("channel3", description="Discovery catalog source ('channel3')")
