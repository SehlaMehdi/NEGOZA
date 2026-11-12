import logging
from fastapi import APIRouter, HTTPException, status
from app.models.buyer import BuyerPrepareRequest, BuyerPrepareResponse
from app.models.seller import SellerRespondRequest, SellerRespondResponse
from app.agents.buyer_agent import buyer_agent
from app.agents.seller_agent import seller_agent

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/agents",
    tags=["Agents"],
)


@router.post(
    "/buyer/prepare",
    response_model=BuyerPrepareResponse,
    status_code=status.HTTP_200_OK,
    summary="Prepare Buyer Agent Negotiation Plan",
    description="Analyzes the customer's purchase goals and formulates a disciplined AI buyer negotiation plan.",
)
async def prepare_buyer_plan(request: BuyerPrepareRequest) -> BuyerPrepareResponse:
    """
    Formulates a structured negotiation plan for the Buyer Agent using Google Gemini.
    """
    try:
        plan = await buyer_agent.prepare_negotiation_plan(request)
        return plan

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
            detail=f"Agent service temporarily unavailable: {err_msg}"
        )

    except Exception as exc:
        logger.exception("Unexpected error in prepare_buyer_plan")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to formulate negotiation plan: {str(exc)}"
        )


@router.post(
    "/seller/respond",
    response_model=SellerRespondResponse,
    status_code=status.HTTP_200_OK,
    summary="Seller Agent Response to Buyer Proposal",
    description="Evaluates a Buyer Agent purchase proposal against merchant commercial constraints and generates an autonomous decision or counter-offer.",
)
async def respond_to_buyer(request: SellerRespondRequest) -> SellerRespondResponse:
    """
    Evaluates buyer proposals and generates commercial counteroffers using Gemini
    with deterministic Python financial rule enforcement.
    """
    try:
        decision = await seller_agent.respond(request)
        return decision

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
            detail=f"Seller Agent service temporarily unavailable: {err_msg}"
        )

    except Exception as exc:
        logger.exception("Unexpected error in respond_to_buyer")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate proposal: {str(exc)}"
        )
