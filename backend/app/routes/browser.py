"""
Browser Automation Routes - Endpoints for KERNEL Cloud Browser lifecycle and page inspection.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from app.models.browser import (
    BrowserStartRequest,
    BrowserStartResponse,
    BrowserInspectRequest,
    BrowserInspectResponse,
    BrowserCloseRequest,
    BrowserCloseResponse,
)
from app.services.kernel_service import kernel_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/browser",
    tags=["Cloud Browser"],
)


@router.post(
    "/start",
    response_model=BrowserStartResponse,
    status_code=status.HTTP_200_OK,
    summary="Start KERNEL Cloud Browser Session",
    description="Provisions an isolated cloud Chromium instance and navigates to the merchant URL.",
)
async def start_browser_session(payload: BrowserStartRequest) -> BrowserStartResponse:
    """
    Creates a new cloud browser session via KERNEL, opens the provided merchant URL,
    and returns session credentials including live view streaming URL.
    """
    try:
        session_info = await kernel_service.start_browser(
            merchant_url=payload.merchant_url,
            timeout_seconds=payload.timeout_seconds or 300,
        )
        return BrowserStartResponse(**session_info)

    except ValueError as val_err:
        err_msg = str(val_err)
        if "KERNEL_API_KEY" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=err_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg
        )

    except PermissionError as perm_err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(perm_err)
        )

    except TimeoutError as time_err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(time_err)
        )

    except ConnectionError as conn_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(conn_err)
        )

    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err)
        )


@router.post(
    "/inspect",
    response_model=BrowserInspectResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect Cloud Browser Page Content",
    description="Executes non-invasive Playwright inspection to retrieve title, URL, text preview, and live view.",
)
async def inspect_browser_page(payload: BrowserInspectRequest) -> BrowserInspectResponse:
    """
    Executes in-browser Playwright inspection on an active KERNEL cloud browser session.
    """
    try:
        inspect_data = await kernel_service.inspect_browser(session_id=payload.session_id)
        return BrowserInspectResponse(**inspect_data)

    except KeyError as key_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(key_err).strip("'\"")
        )

    except ValueError as val_err:
        err_msg = str(val_err)
        if "KERNEL_API_KEY" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=err_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg
        )

    except PermissionError as perm_err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(perm_err)
        )

    except TimeoutError as time_err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(time_err)
        )

    except ConnectionError as conn_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(conn_err)
        )

    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err)
        )


@router.post(
    "/close",
    response_model=BrowserCloseResponse,
    status_code=status.HTTP_200_OK,
    summary="Close KERNEL Cloud Browser Session",
    description="Terminates the active cloud browser session and reclaims resources.",
)
async def close_browser_session(payload: BrowserCloseRequest) -> BrowserCloseResponse:
    """
    Terminates a KERNEL cloud browser session by ID.
    """
    try:
        close_data = await kernel_service.close_browser(session_id=payload.session_id)
        return BrowserCloseResponse(**close_data)

    except KeyError as key_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(key_err).strip("'\"")
        )

    except ValueError as val_err:
        err_msg = str(val_err)
        if "KERNEL_API_KEY" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=err_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg
        )

    except PermissionError as perm_err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(perm_err)
        )

    except TimeoutError as time_err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(time_err)
        )

    except ConnectionError as conn_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(conn_err)
        )

    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err)
        )
