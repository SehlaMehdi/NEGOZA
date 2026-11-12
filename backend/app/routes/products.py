"""
Product Routes - Handles real-time product discovery and search queries via Channel3.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models.product import ProductSearchResponse
from app.services.channel3_service import channel3_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/products",
    tags=["Product Discovery"],
)


@router.get(
    "/search",
    response_model=ProductSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search Products Catalog via Channel3",
    description="Queries the Channel3 catalog across retailers and returns structured product items with prices, images, and merchant URLs.",
)
async def search_products(
    q: str = Query(
        ...,
        min_length=1,
        description="Search keyword or product name (e.g. 'smartwatch')",
        examples=["smartwatch"]
    ),
    limit: Optional[int] = Query(
        20,
        ge=1,
        le=50,
        description="Maximum products to retrieve (default 20, max 50)",
    ),
) -> ProductSearchResponse:
    """
    Search endpoint returning real-time merchant offers and products from Channel3.
    """
    clean_q = q.strip()
    if not clean_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query 'q' cannot be empty or whitespace only.",
        )

    try:
        results = await channel3_service.search_products(query=clean_q, limit=limit or 20)
        return results

    except ValueError as val_err:
        err_msg = str(val_err)
        if "CHANNEL3_API_KEY" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )

    except PermissionError as perm_err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(perm_err),
        )

    except TimeoutError as time_err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(time_err),
        )

    except ConnectionError as conn_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(conn_err),
        )

    except RuntimeError as run_err:
        err_msg = str(run_err)
        if "rate limit" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=err_msg,
        )
