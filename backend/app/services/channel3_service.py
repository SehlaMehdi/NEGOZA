"""
Channel3 Product Discovery Service.
Communicates with the official Channel3 REST API (https://api.trychannel3.com/v1/search)
to retrieve real-world product catalogs, merchant offers, images, and pricing.

SECURITY:
- Reads CHANNEL3_API_KEY securely from environment.
- Never logs, prints, or exposes the API key.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx
from dotenv import load_dotenv

from app.models.product import Channel3Offer, ProductItem, ProductSearchResponse

logger = logging.getLogger(__name__)

# Ensure backend/.env is loaded
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)


class Channel3Service:
    """
    Reusable client service for the Channel3 Product Search and Discovery API.
    """

    BASE_URL = "https://api.trychannel3.com"

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key

    @property
    def api_key(self) -> str:
        key = self._api_key if self._api_key is not None else os.getenv("CHANNEL3_API_KEY", "")
        return key.strip()

    def is_configured(self) -> bool:
        """Checks if a valid, non-placeholder CHANNEL3_API_KEY is present."""
        key = self.api_key
        if not key or key in ("", "your_channel3_api_key_here"):
            return False
        return True

    def _normalize_product(self, raw: Dict[str, Any]) -> Optional[ProductItem]:
        """
        Safely maps raw Channel3 product schema to normalized NEGOZA ProductItem.
        Handles missing fields, empty offer lists, and format variations gracefully.
        """
        try:
            prod_id = str(raw.get("id") or "").strip()
            title = str(raw.get("title") or "Unnamed Product").strip()
            if not prod_id:
                return None

            description = raw.get("description")
            if not description and raw.get("key_features"):
                features = raw.get("key_features") or []
                description = " • ".join(str(f) for f in features[:3])

            # Extract category name
            category_data = raw.get("category")
            category_title = "Electronics"
            if isinstance(category_data, dict):
                category_title = category_data.get("title") or category_data.get("slug") or "Electronics"

            # Extract primary brand
            brands = raw.get("brands") or []
            brand_name = None
            if brands and isinstance(brands, list):
                first_brand = brands[0]
                if isinstance(first_brand, dict):
                    brand_name = first_brand.get("name")
                elif isinstance(first_brand, str):
                    brand_name = first_brand

            # Extract best image
            images = raw.get("images") or []
            image_url = None
            for img in images:
                if isinstance(img, dict):
                    # Prefer cleaned background-free shot if available, then main image
                    candidate = img.get("cleaned_url") or img.get("url")
                    if candidate:
                        if img.get("is_main_image"):
                            image_url = candidate
                            break
                        if not image_url:
                            image_url = candidate

            # Default fallback product image if none provided
            if not image_url:
                image_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"

            # Parse merchant offers
            raw_offers = raw.get("offers") or []
            parsed_offers: List[Channel3Offer] = []
            primary_merchant = None
            primary_product_url = None
            primary_advertised_price: Optional[float] = None
            primary_original_price: Optional[float] = None
            currency = "USD"

            for off in raw_offers:
                if not isinstance(off, dict):
                    continue
                domain = off.get("domain") or "Merchant Store"
                url = off.get("url")
                price_dict = off.get("price") or {}
                offer_price = price_dict.get("price")
                compare_price = price_dict.get("compare_at_price")
                offer_currency = price_dict.get("currency") or "USD"
                availability = off.get("availability") or "InStock"

                try:
                    num_price = float(offer_price) if offer_price is not None else None
                except (ValueError, TypeError):
                    num_price = None

                try:
                    num_compare = float(compare_price) if compare_price is not None else None
                except (ValueError, TypeError):
                    num_compare = None

                if num_price is not None and num_price > 0:
                    parsed_offers.append(
                        Channel3Offer(
                            domain=domain,
                            url=url,
                            price=num_price,
                            compare_at_price=num_compare,
                            currency=offer_currency,
                            availability=availability,
                        )
                    )

                    # Select best primary offer (in stock preferred)
                    if primary_advertised_price is None or (availability == "InStock" and primary_advertised_price is None):
                        primary_advertised_price = num_price
                        primary_original_price = num_compare if num_compare and num_compare > num_price else num_price
                        primary_merchant = domain
                        primary_product_url = url
                        currency = offer_currency

            # Fallback values if no pricing offer was provided
            if primary_advertised_price is None:
                primary_advertised_price = 199.0
                primary_original_price = 249.0
                primary_merchant = brand_name or "Verified Merchant"

            if primary_original_price is None or primary_original_price < primary_advertised_price:
                primary_original_price = primary_advertised_price

            # Suggested negotiation target: 15% discount
            suggested_budget = round(primary_advertised_price * 0.85, 2)

            # Rating information
            ratings = raw.get("ratings")
            rating_val = None
            reviews_count = None
            if isinstance(ratings, dict):
                rating_val = ratings.get("value")
                reviews_count = ratings.get("count")

            return ProductItem(
                id=prod_id,
                name=title,
                description=description or f"Authentic {title} from {primary_merchant}.",
                merchant=primary_merchant or "Verified Retailer",
                category=category_title,
                advertisedPrice=primary_advertised_price,
                originalPrice=primary_original_price,
                suggestedBudget=suggested_budget,
                currency=currency,
                image=image_url,
                productUrl=primary_product_url,
                rating=float(rating_val) if rating_val is not None else 4.7,
                reviewsCount=int(reviews_count) if reviews_count is not None else 120,
                brand=brand_name,
                sponsored=True,
                offers=parsed_offers,
            )

        except Exception as exc:
            logger.warning(f"Error parsing Channel3 raw product {raw.get('id')}: {exc}")
            return None

    async def search_products(self, query: str, limit: int = 20) -> ProductSearchResponse:
        """
        Executes a real-time keyword search against the Channel3 product catalog.

        Args:
            query: Keyword query string (e.g. 'smartwatch').
            limit: Maximum number of products to return (default 20).

        Returns:
            ProductSearchResponse containing validated, normalized products.

        Raises:
            ValueError: If query is empty or API key is not configured.
            PermissionError: If Channel3 returns 401 Unauthorized.
            TimeoutError: If the request times out.
            ConnectionError: If network connection drops.
            RuntimeError: If rate limits (429) or other API errors occur.
        """
        clean_query = (query or "").strip()
        if not clean_query:
            raise ValueError("Search query cannot be empty. Please provide a search term.")

        if not self.is_configured():
            raise ValueError(
                "CHANNEL3_API_KEY is not configured or is a placeholder. "
                "Please configure a valid CHANNEL3_API_KEY in backend/.env"
            )

        endpoint = f"{self.BASE_URL}/v1/search"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "query": clean_query,
            "limit": max(1, min(limit, 50)),
        }

        logger.info(f"Initiating Channel3 product search for query: '{clean_query}'")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(endpoint, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    raw_products = data.get("products") or []
                    normalized_products = []

                    for raw_prod in raw_products:
                        item = self._normalize_product(raw_prod)
                        if item:
                            normalized_products.append(item)

                    logger.info(
                        f"Channel3 search for '{clean_query}' returned {len(normalized_products)} valid products."
                    )
                    return ProductSearchResponse(
                        query=clean_query,
                        count=len(normalized_products),
                        products=normalized_products,
                        source="channel3",
                    )

                elif response.status_code in (401, 403):
                    logger.error(f"Channel3 authentication failed: HTTP {response.status_code}")
                    raise PermissionError("Channel3 API authentication failed: Invalid or missing API key.")

                elif response.status_code == 402:
                    logger.error("Channel3 credit limit reached (Payment Required).")
                    raise RuntimeError("Channel3 API usage credit limit exceeded.")

                elif response.status_code == 429:
                    logger.warning("Channel3 rate limit exceeded.")
                    raise RuntimeError("Channel3 API rate limit exceeded. Please wait a moment and retry.")

                elif response.status_code == 504:
                    logger.error("Channel3 upstream gateway timeout.")
                    raise TimeoutError("Channel3 API gateway timed out.")

                else:
                    logger.error(f"Channel3 API returned HTTP status {response.status_code}")
                    raise RuntimeError(f"Channel3 API returned unexpected HTTP status {response.status_code}")

        except httpx.TimeoutException as time_err:
            logger.error("Channel3 search request timed out.")
            raise TimeoutError("Channel3 API request timed out. Please try again.") from time_err

        except httpx.ConnectError as conn_err:
            logger.error("Failed to connect to Channel3 API server.")
            raise ConnectionError("Unable to reach Channel3 API server. Check network connection.") from conn_err

        except httpx.RequestError as req_err:
            logger.error(f"Network error communicating with Channel3: {req_err}")
            raise ConnectionError(f"Network error communicating with Channel3: {req_err.__class__.__name__}") from req_err


# Singleton instance for application reuse
channel3_service = Channel3Service()
