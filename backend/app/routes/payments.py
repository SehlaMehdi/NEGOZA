"""
Payment Routes - Handles payment gateway status, order creation, and capture in PayPal Sandbox.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from app.models.payments import (
    PayPalStatusResponse,
    PayPalCreateOrderRequest,
    PayPalCreateOrderResponse,
    PayPalCaptureOrderResponse,
)
from app.services.paypal_service import paypal_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"],
)


@router.get(
    "/paypal/status",
    response_model=PayPalStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="PayPal Sandbox Authentication Status",
    description="Validates PayPal Sandbox REST API OAuth 2.0 credentials and returns operational authentication status.",
)
async def get_paypal_status() -> PayPalStatusResponse:
    """
    Requests an OAuth 2.0 access token from PayPal Sandbox using client_credentials grant.
    Confirms sandbox connectivity without storing, logging, or exposing sensitive tokens.
    """
    try:
        auth_result = await paypal_service.verify_sandbox_authentication()
        return PayPalStatusResponse(**auth_result)

    except ValueError as val_err:
        logger.warning(f"PayPal configuration error: {val_err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(val_err)
        )

    except PermissionError as perm_err:
        logger.warning(f"PayPal permission error: {perm_err}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(perm_err)
        )

    except TimeoutError as timeout_err:
        logger.error(f"PayPal timeout error: {timeout_err}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(timeout_err)
        )

    except ConnectionError as conn_err:
        logger.error(f"PayPal connection error: {conn_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(conn_err)
        )

    except RuntimeError as run_err:
        logger.error(f"PayPal runtime error: {run_err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err)
        )


@router.post(
    "/paypal/orders/create",
    response_model=PayPalCreateOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create PayPal Sandbox Order",
    description="Generates a live PayPal Sandbox order for an approved negotiated deal.",
)
async def create_paypal_order(request: PayPalCreateOrderRequest) -> PayPalCreateOrderResponse:
    """
    Creates an order in PayPal Sandbox with intent=CAPTURE for the agreed deal total.
    """
    try:
        order_info = await paypal_service.create_order(
            reference_id=request.negotiation_id,
            description=f"{request.product_name} - NEGOZA Negotiated Deal",
            amount=request.amount,
            currency=request.currency,
        )
        return PayPalCreateOrderResponse(**order_info)

    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except PermissionError as perm_err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(perm_err))
    except Exception as exc:
        logger.exception("Error creating PayPal Sandbox order")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"PayPal order creation failed: {str(exc)}"
        )


@router.post(
    "/paypal/orders/{order_id}/capture",
    response_model=PayPalCaptureOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Capture PayPal Sandbox Order",
    description="Captures an authorized PayPal Sandbox order and returns verified payment outcome.",
)
async def capture_paypal_order(order_id: str) -> PayPalCaptureOrderResponse:
    """
    Attempts to capture payment for a PayPal Sandbox order. Returns authentic status from PayPal.
    """
    try:
        clean_id = order_id.strip()
        capture_info = await paypal_service.capture_order(order_id=clean_id)
        return PayPalCaptureOrderResponse(**capture_info)

    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except PermissionError as perm_err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(perm_err))
    except Exception as exc:
        logger.exception("Error capturing PayPal Sandbox order")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"PayPal order capture failed: {str(exc)}"
        )
