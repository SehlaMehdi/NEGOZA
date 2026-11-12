import json
import logging
import re
from typing import Dict, Any, List, Optional

from app.services.gemini_service import gemini_service
from app.models.buyer import BuyerPrepareRequest, BuyerPrepareResponse

logger = logging.getLogger(__name__)

BUYER_SYSTEM_INSTRUCTION = (
    "You are NEGOZA's Buyer Agent. Your responsibility is to negotiate the best possible purchase terms "
    "on behalf of the customer. You must prioritise the customer's budget and requirements. "
    "Never exceed the customer's maximum acceptable price. Do not invent seller offers, "
    "inventory information, competitor prices or discounts. You must distinguish between proposed "
    "offers and confirmed agreements. You cannot approve or execute a purchase."
)


class BuyerAgent:
    """
    NEGOZA Buyer Agent.
    Represents the customer during autonomous commerce negotiations.
    Prepares strategic negotiation parameters, opening offers, and guardrails
    prior to engaging merchant seller agents.
    """

    def __init__(self):
        self.service = gemini_service

    async def prepare_negotiation_plan(self, req: BuyerPrepareRequest) -> BuyerPrepareResponse:
        """
        Analyzes the product details, advertised price, customer target, and limits
        using Gemini 3.8 Flash to formulate an optimal negotiation plan.
        """
        requirements_str = ", ".join(req.requirements) if req.requirements else "None specified"
        
        prompt = f"""
Prepare a strategic negotiation plan for the following purchase:

Product ID: {req.product_id}
Product Name: {req.product_name}
Merchant: {req.merchant}
Advertised List Price: ${req.advertised_price:.2f}
Customer Target Price: ${req.target_price:.2f}
Customer Maximum Acceptable Price: ${req.max_price:.2f}
Delivery Preference: {req.delivery_preference}
Additional Customer Requirements: {requirements_str}

Formulate a concise, disciplined negotiation plan.
Return ONLY a valid JSON object with the following exact keys:
{{
  "product_summary": "1-2 sentence description of the item and its commercial context",
  "customer_objective": "Clear statement of what the buyer agent aims to secure (price, delivery, terms)",
  "opening_offer": <numeric float representing the initial opening counter-offer; must be less than or equal to customer target price ${req.target_price:.2f}>,
  "strategy": "Concise explanation of the tactical negotiation posture (e.g. initial counter-offer anchoring, concession pacing, trade-offs)",
  "reasoning": "Economic justification for why this opening offer is reasonable without making up false facts",
  "delivery_conditions": "Requested delivery terms (e.g. inclusion of delivery preference without extra fee)",
  "rejection_conditions": [
    "Explicit condition 1 (e.g. any counter-offer exceeding ${req.max_price:.2f})",
    "Explicit condition 2 (e.g. unfulfilled mandatory requirements or hidden surcharges)"
  ]
}}
"""

        raw_response = await self.service.generate_response(
            message=prompt,
            system_instruction=BUYER_SYSTEM_INSTRUCTION,
            response_mime_type="application/json"
        )

        plan_data = self._parse_json_response(raw_response)

        # Enforce strict financial boundaries (Never exceed max_price, opening offer <= target_price and <= advertised_price)
        opening_offer = float(plan_data.get("opening_offer", req.target_price))
        if opening_offer <= 0 or opening_offer > req.max_price:
            # Clamp to safe opening range: slightly below or at target price
            opening_offer = round(min(req.target_price * 0.95, req.max_price), 2)
        elif opening_offer > req.target_price:
            opening_offer = req.target_price

        # Guarantee opening offer never exceeds advertised listed price
        if opening_offer > req.advertised_price:
            opening_offer = req.advertised_price

        # Ensure mandatory rejection condition exists for exceeding max_price
        rejection_conditions = plan_data.get("rejection_conditions") or []
        max_price_rule = f"Final price exceeds customer maximum ceiling of ${req.max_price:.2f}"
        if not any(f"${req.max_price:.2f}" in cond or "exceeds" in cond.lower() for cond in rejection_conditions):
            rejection_conditions.insert(0, max_price_rule)

        return BuyerPrepareResponse(
            status="success",
            agent="buyer",
            product_id=req.product_id,
            product_name=req.product_name,
            merchant=req.merchant,
            advertised_price=req.advertised_price,
            target_price=req.target_price,
            max_price=req.max_price,
            opening_offer=round(opening_offer, 2),
            strategy=plan_data.get("strategy", "Anchored value negotiation with progressive concessions."),
            reasoning=plan_data.get("reasoning", "Initial offer calibrated below list price to establish strong anchoring."),
            delivery_conditions=plan_data.get("delivery_conditions", req.delivery_preference or "Standard delivery"),
            rejection_conditions=rejection_conditions,
            product_summary=plan_data.get("product_summary", f"{req.product_name} offered by {req.merchant}"),
            customer_objective=plan_data.get("customer_objective", f"Acquire {req.product_name} for at or below ${req.target_price:.2f}"),
            model=self.service.default_model
        )

    async def evaluate_seller_counteroffer(
        self,
        product_id: str,
        product_name: str,
        merchant: str,
        advertised_price: float,
        target_price: float,
        max_price: float,
        seller_offered_price: float,
        seller_delivery: str,
        seller_message: str,
        seller_conditions: List[str],
        round_number: int,
        max_rounds: int,
        previous_buyer_offer: float,
        delivery_preference: str = "Free standard delivery",
    ) -> Dict[str, Any]:
        """
        Evaluates a counter-proposal from the Seller Agent during an active negotiation round.
        Enforces customer budget constraints and deterministic Python ceiling limits.
        """
        conditions_str = ", ".join(seller_conditions) if seller_conditions else "Standard terms"

        prompt = f"""
You are NEGOZA's Buyer Agent evaluating a counteroffer from {merchant}'s Seller Agent.

PURCHASE OBJECTIVES & BOUNDARIES:
- Product ID: {product_id}
- Product: {product_name}
- Merchant: {merchant}
- Advertised List Price: ${advertised_price:.2f}
- Customer Target Budget: ${target_price:.2f}
- Customer MAXIMUM ACCEPTABLE PRICE (HARD CEILING): ${max_price:.2f} (NEVER EXCEED THIS)
- Delivery Preference: {delivery_preference}
- Previous Buyer Offer: ${previous_buyer_offer:.2f}

SELLER AGENT PROPOSAL (Round {round_number} of {max_rounds}):
- Seller Offered Price: ${seller_offered_price:.2f}
- Seller Delivery Terms: {seller_delivery}
- Seller Message: "{seller_message}"
- Seller Conditions: {conditions_str}

DECISION RULES:
1. If Seller Offered Price <= ${target_price:.2f}, you SHOULD set status to "accepted".
2. If Seller Offered Price > ${max_price:.2f}, you CANNOT accept under any circumstances. You must either make a "counter_offer" at or below ${max_price:.2f}, or set status to "rejected".
3. If ${target_price:.2f} < Seller Offered Price <= ${max_price:.2f}:
   - You may accept if the price is close enough to target and terms are fair, especially in later rounds ({round_number} of {max_rounds}).
   - Otherwise, you may make a disciplined "counter_offer" between your previous offer (${previous_buyer_offer:.2f}) and the seller's offer, strictly <= ${max_price:.2f}.
4. Return ONLY valid JSON:
{{
  "status": "<accepted | counter_offer | rejected>",
  "counter_price": <numeric float if counter_offer; null if accepted or rejected>,
  "delivery_preference": "<requested delivery terms>",
  "reasoning": "<concise rationale explaining acceptance, counteroffer, or rejection>",
  "message": "<polite response message addressed to the seller agent>"
}}
"""

        raw_response = await self.service.generate_response(
            message=prompt,
            system_instruction=BUYER_SYSTEM_INSTRUCTION,
            response_mime_type="application/json"
        )

        parsed = self._parse_json_response(raw_response)

        return self._enforce_deterministic_constraints(
            parsed_proposal=parsed,
            seller_offered_price=seller_offered_price,
            seller_delivery=seller_delivery,
            target_price=target_price,
            max_price=max_price,
            advertised_price=advertised_price,
            previous_buyer_offer=previous_buyer_offer,
            round_number=round_number,
            max_rounds=max_rounds,
            delivery_preference=delivery_preference
        )

    def _enforce_deterministic_constraints(
        self,
        parsed_proposal: Dict[str, Any],
        seller_offered_price: float,
        seller_delivery: str,
        target_price: float,
        max_price: float,
        previous_buyer_offer: float,
        round_number: int,
        max_rounds: int,
        delivery_preference: str,
        advertised_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        DETERMINISTIC PYTHON VALIDATION FOR BUYER AGENT.
        Enforces customer budget ceilings, advertised price limits, monotonic bid progression,
        and pricing integrity.
        """
        effective_max = float(min(max_price, advertised_price)) if advertised_price is not None and advertised_price > 0 else float(max_price)

        status = str(parsed_proposal.get("status", "counter_offer")).lower().strip()
        if status not in ("accepted", "counter_offer", "rejected"):
            status = "counter_offer"

        counter_price = parsed_proposal.get("counter_price")
        if counter_price is not None:
            try:
                counter_price = float(counter_price)
            except (ValueError, TypeError):
                counter_price = None

        reasoning = str(parsed_proposal.get("reasoning", "")).strip()
        message = str(parsed_proposal.get("message", "")).strip()
        delivery = str(parsed_proposal.get("delivery_preference", delivery_preference)).strip()

        # Rule 1: Ceiling Limit Violation - Never accept above effective max price
        if seller_offered_price > effective_max:
            if status == "accepted":
                logger.warning(
                    f"PYTHON OVERRIDE: Gemini Buyer Agent tried to accept seller offer (${seller_offered_price}) "
                    f"exceeding ceiling (${effective_max}). Overriding to counter_offer/rejected."
                )
                if round_number >= max_rounds:
                    status = "rejected"
                    counter_price = None
                else:
                    status = "counter_offer"
                    counter_price = effective_max

        # Rule 2: Counteroffer Boundaries
        if status == "counter_offer":
            if counter_price is None or counter_price > effective_max:
                # Clamp to customer ceiling
                counter_price = effective_max
            elif counter_price < previous_buyer_offer:
                # Monotonic progression: buyer does not lower their own bid
                counter_price = round(min(effective_max, previous_buyer_offer + (min(seller_offered_price, effective_max) - previous_buyer_offer) * 0.4), 2)
            
            # Ensure counter-offer does not exceed seller's offer or effective ceiling
            if counter_price > seller_offered_price:
                if seller_offered_price <= effective_max:
                    counter_price = seller_offered_price
                    status = "accepted"
                else:
                    counter_price = effective_max

        # Rule 3: Acceptance Check
        elif status == "accepted":
            if seller_offered_price > effective_max:
                status = "counter_offer" if round_number < max_rounds else "rejected"
                counter_price = effective_max if status == "counter_offer" else None
            else:
                counter_price = seller_offered_price
            if not message and status == "accepted":
                message = f"We accept your offer of ${seller_offered_price:.2f} with {seller_delivery} delivery."

        # Hard clamp on counter_price
        if counter_price is not None:
            if counter_price > effective_max:
                counter_price = effective_max
            counter_price = round(counter_price, 2)

        # Rule 4: Sync Message & Reasoning
        currency_symbol = "$"
        if status == "counter_offer" and counter_price is not None:
            # Check for rogue prices in buyer message exceeding effective_max
            price_matches = re.findall(r"\$\s*(\d+(?:\.\d+)?)", message)
            contains_rogue_price = any(float(pm) > effective_max for pm in price_matches if pm.replace('.', '', 1).isdigit())

            if (
                contains_rogue_price
                or not message 
                or (f"{counter_price:.2f}" not in message and f"{counter_price:.0f}" not in message)
            ):
                message = f"We can counter with an offer of {currency_symbol}{counter_price:.2f} with {delivery}."
            if not reasoning:
                reasoning = f"Countering with {currency_symbol}{counter_price:.2f} within customer ceiling limit of {currency_symbol}{effective_max:.2f}."
        elif status == "rejected":
            counter_price = None
            if not message:
                message = f"We cannot accept {currency_symbol}{seller_offered_price:.2f} as it exceeds the customer maximum budget of {currency_symbol}{effective_max:.2f}."
            if not reasoning:
                reasoning = f"Seller offer ({currency_symbol}{seller_offered_price:.2f}) exceeds customer maximum ceiling ({currency_symbol}{effective_max:.2f})."

        return {
            "status": status,
            "agent": "buyer",
            "proposed_price": round(counter_price, 2) if counter_price is not None else None,
            "delivery_conditions": delivery if status == "counter_offer" else seller_delivery,
            "reasoning": reasoning,
            "message": message
        }

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Safely parse JSON response from Gemini, stripping any markdown wrappers if present."""
        clean_text = text.strip()
        # Remove markdown code block if present
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r"\s*```$", "", clean_text)
            clean_text = clean_text.strip()

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as err:
            logger.warning(f"Failed to parse Gemini response as JSON: {err}. Raw text: {text[:200]}")
            # Fallback extraction if partial JSON is present
            match = re.search(r"\{.*\}", clean_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            # Return safe default dict
            return {}


# Shared buyer agent instance
buyer_agent = BuyerAgent()
