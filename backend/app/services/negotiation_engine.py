import asyncio
import logging
import os
import time
import uuid
from typing import List, Optional, Dict, Any

from app.models.negotiation import (
    NegotiationRoundRecord,
    NegotiationStartRequest,
    NegotiationStartResponse,
)
from app.models.buyer import BuyerPrepareRequest
from app.models.seller import MerchantCommercialProfile, SellerRespondResponse
from app.agents.buyer_agent import buyer_agent
from app.agents.seller_agent import seller_agent
from app.services.merchant_data import get_merchant_profile

logger = logging.getLogger(__name__)


class NegotiationEngine:
    """
    Autonomous Agent-to-Agent Negotiation Engine for NEGOZA.
    Orchestrates round-by-round offer exchanges between the Buyer Agent and
    Seller Agent, enforcing deterministic financial boundaries at each step.
    """

    async def negotiate(self, req: NegotiationStartRequest) -> NegotiationStartResponse:
        """
        Executes an autonomous negotiation loop up to req.max_rounds (default 5).
        Returns a complete audit transcript and the verified final outcome.
        """
        negotiation_id = f"neg-{uuid.uuid4().hex[:10]}"
        max_rounds = min(req.max_rounds or 5, 5)  # Enforce hard cap of 5 rounds for prototype

        # Resolve merchant profile
        merchant_profile: MerchantCommercialProfile = (
            req.merchant_constraints or get_merchant_profile(req.product_id, req.merchant_id, advertised_price=req.advertised_price)
        )
        if req.advertised_price and req.advertised_price > 0:
            merchant_profile.listed_price = round(req.advertised_price, 2)
            if merchant_profile.minimum_acceptable_price > merchant_profile.listed_price:
                merchant_profile.minimum_acceptable_price = round(merchant_profile.listed_price * 0.80, 2)
            if merchant_profile.preferred_price is None or merchant_profile.preferred_price <= 0:
                merchant_profile.preferred_price = round(
                    merchant_profile.minimum_acceptable_price + (merchant_profile.listed_price - merchant_profile.minimum_acceptable_price) * 0.70, 2
                )

        merchant_name = req.merchant_name or merchant_profile.merchant_name
        merchant_id = req.merchant_id or merchant_profile.merchant_id

        # Financial floors & ceilings
        min_acceptable_price = merchant_profile.minimum_acceptable_price
        max_buyer_price = min(req.max_price or req.advertised_price, req.advertised_price)
        target_buyer_price = min(req.target_price, max_buyer_price)

        transcript: List[NegotiationRoundRecord] = []
        start_time = time.time()
        total_timeout_budget = float(os.getenv("NEGOTIATION_TIMEOUT_SECONDS", "70.0"))

        final_agreed_price: Optional[float] = None
        final_delivery_terms: Optional[str] = None
        final_status: str = "in_progress"
        summary: str = ""

        logger.info(
            f"Starting Negotiation [{negotiation_id}] for {req.product_name} | "
            f"List: ${req.advertised_price:.2f} | Buyer Target: ${target_buyer_price:.2f} (Max: ${max_buyer_price:.2f}) | "
            f"Merchant Floor: ${min_acceptable_price:.2f}"
        )

        try:
            # =========================================================================
            # ROUND 1: Opening Proposal & Seller Response
            # =========================================================================
            current_round = 1

            # Step 1A: Buyer Agent formulates opening offer
            buyer_prep_req = BuyerPrepareRequest(
                product_id=req.product_id,
                product_name=req.product_name,
                merchant=merchant_name,
                advertised_price=req.advertised_price,
                target_price=target_buyer_price,
                max_price=max_buyer_price,
                delivery_preference=req.delivery_preference or "Free standard delivery",
                requirements=req.requirements or []
            )
            buyer_plan = await buyer_agent.prepare_negotiation_plan(buyer_prep_req)

            buyer_price = buyer_plan.opening_offer
            buyer_delivery = buyer_plan.delivery_conditions

            # Record Buyer Round 1
            transcript.append(
                NegotiationRoundRecord(
                    round_number=current_round,
                    agent="buyer",
                    action="opening_offer",
                    proposed_price=buyer_price,
                    delivery_conditions=buyer_delivery,
                    agent_response=f"Opening offer of ${buyer_price:.2f} for {req.product_name} with {buyer_delivery}.",
                    reasoning=buyer_plan.strategy,
                    round_status="in_progress"
                )
            )

            # Step 1B: Seller Agent evaluates Buyer's opening proposal
            seller_resp: SellerRespondResponse = await seller_agent.evaluate_buyer_proposal(
                buyer_proposed_price=buyer_price,
                delivery_conditions=buyer_delivery,
                product_id=req.product_id,
                product_name=req.product_name,
                merchant_constraints=merchant_profile,
                previous_context=self._build_context_summary(transcript),
                advertised_price=req.advertised_price,
                round_number=current_round
            )

            # Record Seller Round 1 (strictly validated)
            seller_rec_price = seller_resp.offered_price
            if seller_rec_price is not None:
                if seller_rec_price > req.advertised_price:
                    seller_rec_price = req.advertised_price
                seller_rec_price = round(seller_rec_price, 2)

            transcript.append(
                NegotiationRoundRecord(
                    round_number=current_round,
                    agent="seller",
                    action=seller_resp.status,
                    proposed_price=seller_rec_price,
                    delivery_conditions=seller_resp.delivery,
                    agent_response=seller_resp.message,
                    reasoning=seller_resp.reasoning,
                    round_status=seller_resp.status
                )
            )

            # Check Round 1 outcome
            if seller_resp.status == "accepted":
                agreed_price = seller_resp.offered_price or buyer_price
                if self._verify_mutual_agreement(agreed_price, min_acceptable_price, max_buyer_price, req.advertised_price):
                    final_agreed_price = agreed_price
                    final_delivery_terms = seller_resp.delivery
                    final_status = "deal_reached"
                    summary = f"Merchant accepted Buyer Agent's opening offer of ${final_agreed_price:.2f} in Round 1."
                    return self._build_response(negotiation_id, req, merchant_id, merchant_name, final_agreed_price, final_delivery_terms, current_round, final_status, summary, transcript)
                else:
                    final_status = "negotiation_failed"
                    summary = f"Negotiation terminated: agreed price ${agreed_price:.2f} violated commercial or customer pricing constraints."
                    return self._build_response(negotiation_id, req, merchant_id, merchant_name, None, None, current_round, final_status, summary, transcript)

            elif seller_resp.status == "rejected":
                final_status = "negotiation_failed"
                summary = f"Merchant rejected opening proposal of ${buyer_price:.2f} without a counteroffer: {seller_resp.reasoning}"
                return self._build_response(negotiation_id, req, merchant_id, merchant_name, None, None, current_round, final_status, summary, transcript)

            # =========================================================================
            # SUBSEQUENT ROUNDS (2 through max_rounds)
            # =========================================================================
            last_seller_offer = seller_rec_price
            last_seller_delivery = seller_resp.delivery
            last_seller_msg = seller_resp.message
            last_seller_conditions = seller_resp.conditions

            while current_round < max_rounds:
                # Check remaining time budget before initiating another round of Gemini agent calls
                elapsed = time.time() - start_time
                if elapsed >= (total_timeout_budget - 18.0):
                    logger.warning(
                        f"Negotiation [{negotiation_id}] approaching timeout budget "
                        f"({elapsed:.1f}s / {total_timeout_budget}s). Ending multi-round loop gracefully."
                    )
                    final_status = "maximum_rounds_reached"
                    summary = (
                        f"Negotiation concluded after {current_round} rounds within time budget. "
                        f"Final Buyer offer: ${buyer_price:.2f} vs Final Seller offer: ${last_seller_offer:.2f}."
                    )
                    return self._build_response(
                        negotiation_id, req, merchant_id, merchant_name, None, None, current_round, final_status, summary, transcript
                    )

                current_round += 1

                # Step A: Buyer Agent evaluates Seller's counteroffer
                buyer_eval = await buyer_agent.evaluate_seller_counteroffer(
                    product_id=req.product_id,
                    product_name=req.product_name,
                    merchant=merchant_name,
                    advertised_price=req.advertised_price,
                    target_price=target_buyer_price,
                    max_price=max_buyer_price,
                    seller_offered_price=last_seller_offer,
                    seller_delivery=last_seller_delivery,
                    seller_message=last_seller_msg,
                    seller_conditions=last_seller_conditions,
                    round_number=current_round,
                    max_rounds=max_rounds,
                    previous_buyer_offer=buyer_price,
                    delivery_preference=req.delivery_preference or "Free standard delivery"
                )

                # Record Buyer turn (strictly validated)
                buyer_rec_price = buyer_eval["proposed_price"]
                if buyer_rec_price is not None:
                    if buyer_rec_price > max_buyer_price:
                        buyer_rec_price = max_buyer_price
                    buyer_rec_price = round(buyer_rec_price, 2)

                transcript.append(
                    NegotiationRoundRecord(
                        round_number=current_round,
                        agent="buyer",
                        action=buyer_eval["status"],
                        proposed_price=buyer_rec_price,
                        delivery_conditions=buyer_eval["delivery_conditions"],
                        agent_response=buyer_eval["message"],
                        reasoning=buyer_eval["reasoning"],
                        round_status=buyer_eval["status"]
                    )
                )

                if buyer_eval["status"] == "accepted":
                    agreed_price = last_seller_offer
                    if self._verify_mutual_agreement(agreed_price, min_acceptable_price, max_buyer_price, req.advertised_price):
                        final_agreed_price = agreed_price
                        final_delivery_terms = last_seller_delivery
                        final_status = "deal_reached"
                        summary = f"Buyer Agent accepted Seller's offer of ${final_agreed_price:.2f} with {final_delivery_terms} in Round {current_round}."
                        return self._build_response(negotiation_id, req, merchant_id, merchant_name, final_agreed_price, final_delivery_terms, current_round, final_status, summary, transcript)
                    else:
                        final_status = "negotiation_failed"
                        summary = f"Negotiation terminated: agreed price ${agreed_price:.2f} violated customer or commercial pricing boundaries."
                        return self._build_response(negotiation_id, req, merchant_id, merchant_name, None, None, current_round, final_status, summary, transcript)

                elif buyer_eval["status"] == "rejected":
                    final_status = "negotiation_failed"
                    summary = f"Buyer Agent declined Seller's counter-proposal of ${last_seller_offer:.2f} in Round {current_round}: {buyer_eval['reasoning']}"
                    return self._build_response(negotiation_id, req, merchant_id, merchant_name, None, None, current_round, final_status, summary, transcript)

                # Buyer counter-offered
                buyer_price = buyer_rec_price
                buyer_delivery = buyer_eval["delivery_conditions"]

                # Step B: Seller Agent evaluates Buyer's new counteroffer
                seller_resp = await seller_agent.evaluate_buyer_proposal(
                    buyer_proposed_price=buyer_price,
                    delivery_conditions=buyer_delivery,
                    product_id=req.product_id,
                    product_name=req.product_name,
                    merchant_constraints=merchant_profile,
                    previous_context=self._build_context_summary(transcript),
                    advertised_price=req.advertised_price,
                    round_number=current_round
                )

                # Record Seller turn (strictly validated)
                seller_rec_price = seller_resp.offered_price
                if seller_rec_price is not None:
                    if seller_rec_price > req.advertised_price:
                        seller_rec_price = req.advertised_price
                    seller_rec_price = round(seller_rec_price, 2)

                transcript.append(
                    NegotiationRoundRecord(
                        round_number=current_round,
                        agent="seller",
                        action=seller_resp.status,
                        proposed_price=seller_rec_price,
                        delivery_conditions=seller_resp.delivery,
                        agent_response=seller_resp.message,
                        reasoning=seller_resp.reasoning,
                        round_status=seller_resp.status
                    )
                )

                if seller_resp.status == "accepted":
                    agreed_price = seller_resp.offered_price or buyer_price
                    if self._verify_mutual_agreement(agreed_price, min_acceptable_price, max_buyer_price, req.advertised_price):
                        final_agreed_price = agreed_price
                        final_delivery_terms = seller_resp.delivery
                        final_status = "deal_reached"
                        summary = f"Seller Agent accepted Buyer Agent's counter-offer of ${final_agreed_price:.2f} in Round {current_round}."
                        return self._build_response(negotiation_id, req, merchant_id, merchant_name, final_agreed_price, final_delivery_terms, current_round, final_status, summary, transcript)
                    else:
                        final_status = "negotiation_failed"
                        summary = f"Negotiation terminated: agreed price ${agreed_price:.2f} violated commercial or customer pricing boundaries."
                        return self._build_response(negotiation_id, req, merchant_id, merchant_name, None, None, current_round, final_status, summary, transcript)

                elif seller_resp.status == "rejected":
                    final_status = "negotiation_failed"
                    summary = f"Seller Agent rejected counter-proposal of ${buyer_price:.2f} in Round {current_round}."
                    return self._build_response(negotiation_id, req, merchant_id, merchant_name, None, None, current_round, final_status, summary, transcript)

                # Update seller offer for potential next round
                last_seller_offer = seller_rec_price
                last_seller_delivery = seller_resp.delivery
                last_seller_msg = seller_resp.message
                last_seller_conditions = seller_resp.conditions

            # Reached maximum allowed rounds without convergence
            if max_buyer_price < min_acceptable_price:
                final_status = "negotiation_failed"
                summary = (
                    f"Negotiation terminated without agreement. No zone of possible agreement exists: "
                    f"Buyer maximum budget (${max_buyer_price:.2f}) is below Seller minimum acceptable price (${min_acceptable_price:.2f})."
                )
            else:
                final_status = "maximum_rounds_reached"
                summary = (
                    f"Negotiation reached maximum limit of {max_rounds} rounds without reaching full agreement. "
                    f"Final Buyer offer: ${buyer_price:.2f} vs Final Seller offer: ${last_seller_offer:.2f}."
                )
            return self._build_response(
                negotiation_id, req, merchant_id, merchant_name, None, None, current_round, final_status, summary, transcript
            )

        except Exception as exc:
            logger.exception(f"Error during negotiation loop {negotiation_id}: {exc}")
            # Ensure every negotiation returns structured audit data even on failure
            transcript.append(
                NegotiationRoundRecord(
                    round_number=len(transcript) // 2 + 1,
                    agent="buyer",
                    action="rejected",
                    proposed_price=None,
                    delivery_conditions="none",
                    agent_response="Negotiation halted due to service exception.",
                    reasoning=str(exc),
                    round_status="negotiation_failed"
                )
            )
            return self._build_response(
                negotiation_id,
                req,
                merchant_id,
                merchant_name,
                None,
                None,
                max(1, len(transcript) // 2),
                "negotiation_failed",
                f"Negotiation terminated due to service disruption: {str(exc)}",
                transcript
            )

    def _verify_mutual_agreement(
        self,
        agreed_price: float,
        min_acceptable_price: float,
        max_buyer_price: float,
        advertised_price: Optional[float] = None
    ) -> bool:
        """
        Deterministic Python validation to guarantee that a claimed deal is strictly
        within both the buyer's maximum ceiling and merchant's minimum price floor,
        and never exceeds the public advertised list price.
        """
        if agreed_price < min_acceptable_price:
            logger.error(f"VIOLATION: Deal price (${agreed_price}) is below merchant minimum (${min_acceptable_price}).")
            return False
        if agreed_price > max_buyer_price:
            logger.error(f"VIOLATION: Deal price (${agreed_price}) exceeds buyer maximum (${max_buyer_price}).")
            return False
        if advertised_price is not None and agreed_price > advertised_price:
            logger.error(f"VIOLATION: Deal price (${agreed_price}) exceeds advertised price (${advertised_price}).")
            return False
        return True

    def _build_context_summary(self, transcript: List[NegotiationRoundRecord]) -> List[Dict[str, Any]]:
        """Converts transcript history into compact context for subsequent AI reasoning."""
        return [
            {
                "round": r.round_number,
                "agent": r.agent,
                "action": r.action,
                "price": r.proposed_price,
                "delivery": r.delivery_conditions,
                "message": r.agent_response
            }
            for r in transcript
        ]

    def _build_response(
        self,
        negotiation_id: str,
        req: NegotiationStartRequest,
        merchant_id: str,
        merchant_name: str,
        agreed_price: Optional[float],
        delivery_terms: Optional[str],
        rounds_count: int,
        status: str,
        summary: str,
        transcript: List[NegotiationRoundRecord]
    ) -> NegotiationStartResponse:
        return NegotiationStartResponse(
            negotiation_id=negotiation_id,
            product_id=req.product_id,
            product_name=req.product_name,
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            initial_advertised_price=req.advertised_price,
            target_price=req.target_price,
            max_price=req.max_price or req.advertised_price,
            final_agreed_price=round(agreed_price, 2) if agreed_price is not None else None,
            delivery_terms=delivery_terms,
            rounds_count=rounds_count,
            status=status,
            summary=summary,
            transcript=transcript
        )


# Singleton negotiation engine instance
negotiation_engine = NegotiationEngine()
