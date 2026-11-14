import logging
from fastapi import APIRouter, HTTPException, status
from app.models.negotiation import NegotiationStartRequest, NegotiationStartResponse
from app.services.negotiation_engine import negotiation_engine

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/negotiation",
    tags=["Negotiation"],
)


@router.post(
    "/start",
    response_model=NegotiationStartResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Autonomous Agent-to-Agent Negotiation",
    description="Orchestrates an autonomous negotiation loop between the Buyer Agent and Seller Agent until an agreement is reached, rejected, or maximum rounds are exhausted.",
)
async def start_negotiation(request: NegotiationStartRequest) -> NegotiationStartResponse:
    """
    Executes an autonomous multi-round negotiation between the AI Buyer Agent
    and AI Seller Agent, returning the complete auditable transcript and verified outcome.
    """
    try:
        outcome = await negotiation_engine.negotiate(request)
        return outcome

    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )

    except PermissionError as perm_err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(perm_err)
        )

    except RuntimeError as run_err:
        err_msg = str(run_err)
        if "quota" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=err_msg
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Negotiation service unavailable: {err_msg}"
        )

    except (TimeoutError, asyncio.TimeoutError) as timeout_err:
        logger.error(f"Negotiation request timed out: {timeout_err}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Negotiation timed out waiting for AI agents. Please try again with a competitive opening offer or adjust budget."
        )

    except Exception as exc:
        logger.exception("Unexpected error in start_negotiation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute negotiation: {str(exc)}"
        )
