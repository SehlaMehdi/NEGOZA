import json
import logging
import re
from typing import Dict, Any, Optional, List

from app.services.gemini_service import gemini_service
from app.models.seller import (
    MerchantCommercialProfile,
    SellerRespondRequest,
    SellerRespondResponse,
)
from app.services.merchant_data import get_merchant_profile

logger = logging.getLogger(__name__)

SELLER_SYSTEM_INSTRUCTION = (
    "You are NEGOZA's Seller Agent. You represent the merchant, not the buyer. "
    "Your objective is to maximise the merchant's commercial value while considering reasonable offers. "
    "You must distinguish between the advertised list price, the merchant's preferred selling price, "
    "and the absolute minimum acceptable price. "
    "Do not treat the minimum acceptable price as the price at which you must immediately accept every offer. "
    "When a buyer makes an offer below the preferred price, you must generally counteroffer instead of immediately accepting. "
    "Make progressive, measured concessions across negotiation rounds towards a mutually acceptable middle ground. "
    "You must never offer or accept a price below the merchant's configured minimum acceptable price. "
    "You must never counteroffer above the advertised list price. "
    "You may consider free delivery or other benefits only if merchant rules permit them. "
    "Never invent inventory, discounts or promotional policies. "
    "Evaluate every buyer proposal against the actual merchant commercial constraints."
)


class SellerAgent:
    """
    NEGOZA Seller Agent.
    Represents the merchant in autonomous commerce negotiations.
    Evaluates buyer proposals against hard merchant commercial constraints,
    generating disciplined counteroffers or acceptance decisions.
    
    IMPORTANT: All outputs are passed through deterministic Python validation
    to ensure financial floors, inventory, and delivery policies are strictly enforced.
    """

    def __init__(self):
        self.service = gemini_service

    async def evaluate_buyer_proposal(
        self,
        buyer_proposed_price: float,
        delivery_conditions: Optional[str] = "Free standard delivery",
        product_id: str = "prod-1",
        product_name: str = "Product",
        merchant_constraints: Optional[MerchantCommercialProfile] = None,
        previous_context: Optional[List[Dict[str, Any]]] = None,
        advertised_price: Optional[float] = None,
        round_number: Optional[int] = None,
    ) -> SellerRespondResponse:
        """
        Evaluates a buyer proposal by querying Gemini with strict merchant parameters,
        then applying deterministic Python-level constraint enforcement.
        """
        # Resolve merchant profile (use passed constraints or look up simulated database)
        merchant: MerchantCommercialProfile = merchant_constraints or get_merchant_profile(product_id, advertised_price=advertised_price)
        if advertised_price is not None and advertised_price > 0:
            merchant.listed_price = round(advertised_price, 2)
            if merchant.minimum_acceptable_price > merchant.listed_price:
                merchant.minimum_acceptable_price = round(merchant.listed_price * 0.80, 2)
            if merchant.preferred_price is None or merchant.preferred_price <= 0:
                merchant.preferred_price = round(
                    merchant.minimum_acceptable_price + (merchant.listed_price - merchant.minimum_acceptable_price) * 0.70, 2
                )

        # Resolve current round number
        if round_number is None:
            if previous_context:
                round_number = (len(previous_context) // 2) + 1
            else:
                round_number = 1

        # Context formatting
        context_str = "None (initial round)"
        if previous_context:
            context_str = json.dumps(previous_context, indent=2)

        promo_rules_str = "\n".join(f"- {rule}" for rule in merchant.promotional_rules) if merchant.promotional_rules else "- Standard pricing applies."

        prompt = f"""
Evaluate the following Buyer Agent purchase proposal on behalf of the merchant:

PRODUCT & PROPOSAL DETAILS:
- Product ID: {merchant.product_id}
- Product Name: {product_name}
- Merchant Name: {merchant.merchant_name} (ID: {merchant.merchant_id})
- Advertised Listed Price: ${merchant.listed_price:.2f}
- Buyer Proposed Price: ${buyer_proposed_price:.2f}
- Buyer Requested Delivery: {delivery_conditions or "Free standard delivery"}
- Current Negotiation Round: Round {round_number}
- Previous Negotiation Context:
{context_str}

MERCHANT COMMERCIAL PRICING STRATEGY & BOUNDARIES:
- Advertised Listed Price: ${merchant.listed_price:.2f} (Catalog public price)
- Preferred Selling Price: ${merchant.preferred_price:.2f} (Merchant's target price to maintain commercial profitability)
- Minimum Acceptable Price (Absolute Floor): ${merchant.minimum_acceptable_price:.2f} (Strict cost floor; NEVER go below this)
- Available Inventory: {merchant.available_inventory} units
- Maximum Permitted Discount: ${merchant.maximum_permitted_discount:.2f} below list price
- Delivery Cost: ${merchant.delivery_cost:.2f}
- Free Delivery Allowed by Merchant Policy: {"YES (Allowed)" if merchant.free_delivery_allowed else "NO (Strictly Forbidden - Buyer must pay delivery fee)"}
- Merchant Promotional Rules:
{promo_rules_str}

STRATEGIC NEGOTIATION RULES & COUNTEROFFER BEHAVIOUR:
1. OUT OF STOCK: If available inventory is 0, status must be "rejected".
2. ABSOLUTE FLOOR: If Buyer Proposed Price is below Minimum Acceptable Price (${merchant.minimum_acceptable_price:.2f}), you CANNOT accept it under any circumstances. You must either make a disciplined "counter_offer" at or above ${merchant.minimum_acceptable_price:.2f}, or set status to "rejected".
3. PREFERRED PRICE & OPENING OFFERS:
   - When the Buyer makes an offer below your Preferred Selling Price (${merchant.preferred_price:.2f}), do NOT immediately accept, especially on opening offers (Round 1 or 2). You represent the merchant and must protect margin.
   - Formulate a strategic counteroffer between your preferred price and list price to anchor the negotiation.
4. PROGRESSIVE CONCESSIONS ACROSS ROUNDS:
   - Move progressively towards a mutually acceptable price across rounds.
   - Make reasonable, measured concessions across negotiation rounds. Do NOT repeat the exact same counteroffer unnecessarily if the buyer has increased their offer.
   - Do NOT jump directly to the minimum price floor on the first counteroffer. Concede in rational, gradual steps.
5. STRATEGIC ACCEPTANCE CRITERIA:
   - If Buyer Proposed Price >= Preferred Selling Price (${merchant.preferred_price:.2f}), accept the offer because it meets the merchant's target.
   - If Buyer Proposed Price is between Minimum Acceptable Price and Preferred Selling Price:
     * In early rounds (Round 1): Counteroffer instead of accepting.
     * In subsequent rounds (Round >= 2): If the buyer's offer represents a mutually acceptable compromise after concessions and is above Minimum Acceptable Price (${merchant.minimum_acceptable_price:.2f}), you MAY accept to finalize the sale.
6. HARD PRICING CEILING & SEPARATION:
   - Seller product counteroffers must NEVER exceed the Advertised Listed Price (${merchant.listed_price:.2f}).
   - Never roll delivery charges into offered_price. Keep product price and delivery terms strictly separate.
7. DELIVERY POLICY:
   - If Free Delivery Allowed is NO, delivery MUST NOT be free. A delivery surcharge of ${merchant.delivery_cost:.2f} must apply.
   - If Free Delivery Allowed is YES, free delivery can be offered if the price margin justifies it.

Return ONLY a valid JSON object with the following exact keys:
{{
  "status": "<accepted | counter_offer | rejected>",
  "offered_price": <numeric float if accepted or counter_offer; null if rejected. MUST be between ${merchant.minimum_acceptable_price:.2f} and ${merchant.listed_price:.2f}>,
  "delivery": "<free | paid (${merchant.delivery_cost:.2f}) | standard>",
  "reasoning": "<Commercial rationale explaining your pricing strategy, concession pace, and merchant margin considerations>",
  "conditions": ["<array of commercial conditions, warranties, or delivery terms>"],
  "message": "<Polite, professional counter-proposal or decision message addressed to the buyer agent>"
}}
"""

        raw_text = await self.service.generate_response(
            message=prompt,
            system_instruction=SELLER_SYSTEM_INSTRUCTION,
            response_mime_type="application/json"
        )

        raw_parsed = self._parse_json_response(raw_text)

        # Apply deterministic Python enforcement (Gemini must not be trusted to enforce financial limits)
        enforced_response = self._enforce_deterministic_constraints(
            raw_proposal=raw_parsed,
            buyer_price=buyer_proposed_price,
            buyer_delivery=delivery_conditions,
            product_name=product_name,
            merchant=merchant,
            round_number=round_number,
            previous_context=previous_context
        )

        return enforced_response

    async def respond(self, req: SellerRespondRequest) -> SellerRespondResponse:
        """Convenience method accepting a SellerRespondRequest Pydantic object."""
        return await self.evaluate_buyer_proposal(
            buyer_proposed_price=req.buyer_proposed_price,
            delivery_conditions=req.delivery_conditions,
            product_id=req.product_id,
            product_name=req.product_name or "Product",
            merchant_constraints=req.merchant_constraints,
            previous_context=req.previous_context,
            round_number=req.round_number
        )

    def _enforce_deterministic_constraints(
        self,
        raw_proposal: Dict[str, Any],
        buyer_price: float,
        buyer_delivery: Optional[str],
        product_name: str,
        merchant: MerchantCommercialProfile,
        round_number: int = 1,
        previous_context: Optional[List[Dict[str, Any]]] = None,
    ) -> SellerRespondResponse:
        """
        DETERMINISTIC PYTHON VALIDATION LAYER.
        Guarantees that all financial boundaries, inventory limits, and delivery policies
        are strictly enforced regardless of AI generation.
        """
        min_price = float(merchant.minimum_acceptable_price)
        list_price = float(merchant.listed_price)
        pref_price = float(merchant.preferred_price or (min_price + (list_price - min_price) * 0.70))

        if min_price > list_price:
            min_price = list_price
        if pref_price > list_price:
            pref_price = list_price
        if pref_price < min_price:
            pref_price = min_price
        
        # 1. Out of Stock Rule
        if merchant.available_inventory <= 0:
            return SellerRespondResponse(
                status="rejected",
                agent="seller",
                offered_price=None,
                delivery="none",
                reasoning=f"Product {product_name} is currently out of stock ({merchant.available_inventory} available).",
                conditions=["Out of stock"],
                message=f"We apologize, but {product_name} is currently out of stock."
            )

        status = str(raw_proposal.get("status", "counter_offer")).lower().strip()
        if status not in ("accepted", "counter_offer", "rejected"):
            status = "counter_offer"

        offered_price = raw_proposal.get("offered_price")
        if offered_price is not None:
            try:
                offered_price = float(offered_price)
            except (ValueError, TypeError):
                offered_price = None

        delivery = str(raw_proposal.get("delivery", "standard")).lower().strip()
        reasoning = str(raw_proposal.get("reasoning", "")).strip()
        conditions = raw_proposal.get("conditions") if isinstance(raw_proposal.get("conditions"), list) else []
        message = str(raw_proposal.get("message", "")).strip()

        # Extract previous offers from context
        prev_seller_offers = [
            float(item["price"]) for item in (previous_context or [])
            if item.get("agent") == "seller" and item.get("price") is not None
        ]
        last_seller_offer = prev_seller_offers[-1] if prev_seller_offers else None

        prev_buyer_offers = [
            float(item["price"]) for item in (previous_context or [])
            if item.get("agent") == "buyer" and item.get("price") is not None
        ]
        last_buyer_offer = prev_buyer_offers[-1] if prev_buyer_offers else None

        # 2. Free Delivery Policy Enforcement
        if not merchant.free_delivery_allowed:
            # Free shipping is strictly prohibited by merchant policy
            if "free" in delivery:
                delivery = f"paid (${merchant.delivery_cost:.2f})"
            if not any(f"${merchant.delivery_cost:.2f}" in c or "shipping fee" in c.lower() for c in conditions):
                conditions.append(f"Standard shipping fee of ${merchant.delivery_cost:.2f} applies")
        else:
            # Free shipping is permitted
            if "free" in delivery or "free" in (buyer_delivery or "").lower():
                delivery = "free"

        # 3. Commercial Strategy & Floor Enforcement
        if buyer_price < min_price:
            # Proposal is below merchant's absolute cost floor. NEVER ACCEPT.
            if status == "accepted":
                logger.warning(
                    f"PYTHON OVERRIDE: Gemini erroneously accepted buyer offer (${buyer_price}) "
                    f"below minimum acceptable price (${min_price}). Overriding to counter_offer."
                )
                status = "counter_offer"
            
            if status == "counter_offer":
                # Ensure counter-offer price is at or above minimum acceptable price
                if offered_price is None or offered_price < min_price:
                    if last_seller_offer is not None and last_seller_offer > min_price:
                        # Concede progressively from last counteroffer
                        concession = max(1.0, round((last_seller_offer - min_price) * 0.25, 2))
                        offered_price = max(min_price, round(last_seller_offer - concession, 2))
                    else:
                        # Formulate opening counteroffer near preferred price
                        offered_price = round(pref_price + (list_price - pref_price) * 0.35, 2)
                    reasoning += f" (Enforced: counter-offer calibrated to protect merchant minimum floor of ${min_price:.2f})."
                elif offered_price > list_price:
                    logger.warning(
                        f"PYTHON OVERRIDE: Gemini generated seller counteroffer (${offered_price}) "
                        f"exceeding listed price (${list_price}). Clamping to listed price."
                    )
                    offered_price = list_price
            else:
                # status == 'rejected'
                offered_price = None

        elif buyer_price >= list_price:
            # Buyer offered at or above list price
            status = "accepted"
            offered_price = list_price
            reasoning = "Buyer proposal meets or exceeds standard listed price."

        elif buyer_price >= pref_price:
            # Buyer offer meets or exceeds merchant preferred target price
            status = "accepted"
            offered_price = round(buyer_price, 2)
            if not reasoning:
                reasoning = f"Buyer proposed price of ${buyer_price:.2f} meets merchant preferred target price (${pref_price:.2f})."

        else:
            # Buyer price is between minimum_acceptable_price and preferred_price: min_price <= buyer_price < pref_price
            if round_number <= 1 or last_seller_offer is None:
                # In opening round, protect margin and do not fold immediately
                if status == "accepted" and buyer_price < pref_price * 0.99:
                    logger.info(
                        f"PYTHON OVERRIDE: Seller Agent countering opening offer (${buyer_price}) "
                        f"below preferred target price (${pref_price})."
                    )
                    status = "counter_offer"
                    if offered_price is None or offered_price <= buyer_price or offered_price < min_price:
                        offered_price = round(pref_price + (list_price - pref_price) * 0.35, 2)
                    reasoning = f"Opening offer of ${buyer_price:.2f} is below preferred target price (${pref_price:.2f}). Counteroffering to establish commercial middle ground."
                elif status == "accepted":
                    offered_price = round(buyer_price, 2)
                elif status == "counter_offer":
                    if offered_price is None or offered_price < min_price:
                        offered_price = round(max(pref_price, buyer_price + (list_price - buyer_price) * 0.50), 2)
            else:
                # Subsequent rounds: Strategic evaluation
                if status == "accepted":
                    offered_price = round(buyer_price, 2)
                elif status == "counter_offer":
                    if offered_price is None or offered_price < min_price:
                        offered_price = round(max(buyer_price, min_price), 2)

        # 4. Enforce offered_price bounds & progressive concessions for counter_offer
        if status in ("accepted", "counter_offer"):
            if offered_price is None:
                offered_price = list_price if status == "counter_offer" else buyer_price

            # HARD CLAMPS: strictly bounded by [min_price, list_price]
            if offered_price > list_price:
                logger.warning(
                    f"PYTHON OVERRIDE: Seller counteroffer (${offered_price}) exceeded advertised listed price (${list_price}). "
                    f"Clamping to listed price ${list_price}."
                )
                offered_price = list_price
            elif offered_price < min_price:
                logger.warning(
                    f"PYTHON OVERRIDE: Seller counteroffer (${offered_price}) fell below minimum acceptable floor (${min_price}). "
                    f"Clamping to minimum price ${min_price}."
                )
                offered_price = min_price

            # Progressive concession enforcement:
            # A) Seller counteroffer should not move backwards (increase) above previous counteroffer
            if status == "counter_offer" and last_seller_offer is not None:
                if offered_price > last_seller_offer:
                    logger.warning(
                        f"PYTHON OVERRIDE: Seller counteroffer (${offered_price}) increased above previous offer (${last_seller_offer}). "
                        f"Clamping to previous offer."
                    )
                    offered_price = last_seller_offer
                # B) If buyer conceded upwards, seller should not repeat exact same counteroffer unless at floor
                elif (
                    offered_price == last_seller_offer
                    and last_buyer_offer is not None
                    and buyer_price > last_buyer_offer
                    and last_seller_offer > min_price + 0.50
                ):
                    concession_step = max(1.0, round((last_seller_offer - max(buyer_price, min_price)) * 0.25, 2))
                    offered_price = max(min_price, round(last_seller_offer - concession_step, 2))

            # Overlap check: If seller counteroffer is at or below buyer offer, deal is reached
            if status == "counter_offer" and offered_price <= buyer_price:
                status = "accepted"
                offered_price = round(buyer_price, 2)
                reasoning = f"Buyer offer of ${buyer_price:.2f} meets or exceeds seller counteroffer threshold."

            offered_price = round(offered_price, 2)

        # 5. Format consistent message and reasoning
        currency_symbol = "$"
        if status == "accepted":
            if not message or "offer" not in message.lower() or "reject" in message.lower():
                delivery_note = "with free delivery" if delivery == "free" else f"plus {delivery} delivery"
                message = f"We are pleased to accept your offer of {currency_symbol}{offered_price:.2f} {delivery_note}."
            if not reasoning:
                reasoning = f"Offer of {currency_symbol}{offered_price:.2f} satisfies merchant commercial margin requirements."

        elif status == "counter_offer":
            delivery_phrase = "with free delivery" if delivery == "free" else f"plus ${merchant.delivery_cost:.2f} delivery fee"
            
            # Check for rogue dollar amounts in message that exceed listed price or contradict offered_price
            price_matches = re.findall(r"\$\s*(\d+(?:\.\d+)?)", message)
            contains_rogue_price = False
            for pm in price_matches:
                try:
                    if float(pm) > list_price:
                        contains_rogue_price = True
                        break
                except ValueError:
                    pass

            # Synchronize message if AI generated an invalid price or message didn't match enforced price
            if (
                contains_rogue_price
                or not message 
                or (f"{offered_price:.0f}" not in message and f"{offered_price:.2f}" not in message)
            ):
                message = f"I can offer {currency_symbol}{offered_price:.2f} {delivery_phrase}."
            elif not merchant.free_delivery_allowed and "free delivery" in message.lower():
                message = re.sub(r"with free delivery|free shipping|free delivery", f"plus ${merchant.delivery_cost:.2f} shipping fee", message, flags=re.IGNORECASE)
            
            if not reasoning:
                reasoning = f"Counter-offer of {currency_symbol}{offered_price:.2f} is within permitted discount range while protecting merchant margin."

        else:
            # Rejected
            if not message:
                message = f"We cannot accept {currency_symbol}{buyer_price:.2f}. The offer is below our commercial feasibility threshold."
            if not reasoning:
                reasoning = f"Buyer proposed price of {currency_symbol}{buyer_price:.2f} is below minimum acceptable threshold of {currency_symbol}{min_price:.2f}."

        return SellerRespondResponse(
            status=status,
            agent="seller",
            offered_price=offered_price,
            delivery=delivery,
            reasoning=reasoning,
            conditions=conditions,
            message=message
        )

        # 5. Format consistent message and reasoning
        currency_symbol = "$"
        if status == "accepted":
            if not message or "offer" not in message.lower() or "reject" in message.lower():
                delivery_note = "with free delivery" if delivery == "free" else f"plus {delivery} delivery"
                message = f"We are pleased to accept your offer of {currency_symbol}{offered_price:.2f} {delivery_note}."
            if not reasoning:
                reasoning = f"Offer of {currency_symbol}{offered_price:.2f} satisfies merchant commercial margin requirements."

        elif status == "counter_offer":
            delivery_phrase = "with free delivery" if delivery == "free" else f"plus ${merchant.delivery_cost:.2f} delivery fee"
            
            # Check for rogue dollar amounts in message that exceed listed price
            price_matches = re.findall(r"\$\s*(\d+(?:\.\d+)?)", message)
            contains_rogue_price = False
            for pm in price_matches:
                try:
                    if float(pm) > list_price:
                        contains_rogue_price = True
                        break
                except ValueError:
                    pass

            # Synchronize message if AI generated an invalid price or message didn't match enforced price
            if (
                contains_rogue_price
                or not message 
                or (f"{offered_price:.0f}" not in message and f"{offered_price:.2f}" not in message)
            ):
                message = f"I can offer {currency_symbol}{offered_price:.2f} {delivery_phrase}."
            elif not merchant.free_delivery_allowed and "free delivery" in message.lower():
                message = re.sub(r"with free delivery|free shipping|free delivery", f"plus ${merchant.delivery_cost:.2f} shipping fee", message, flags=re.IGNORECASE)
            
            if not reasoning:
                reasoning = f"Counter-offer of {currency_symbol}{offered_price:.2f} is within permitted discount range while protecting merchant margin."

        else:
            # Rejected
            if not message:
                message = f"We cannot accept {currency_symbol}{buyer_price:.2f}. The offer is below our commercial feasibility threshold."
            if not reasoning:
                reasoning = f"Buyer proposed price of {currency_symbol}{buyer_price:.2f} is below minimum acceptable threshold of {currency_symbol}{min_price:.2f}."

        return SellerRespondResponse(
            status=status,
            agent="seller",
            offered_price=offered_price,
            delivery=delivery,
            reasoning=reasoning,
            conditions=conditions,
            message=message
        )

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Safely parse JSON response from Gemini, removing any markdown code blocks."""
        clean_text = text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r"\s*```$", "", clean_text)
            clean_text = clean_text.strip()

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as err:
            logger.warning(f"Failed to parse Seller Agent Gemini response as JSON: {err}. Raw text: {text[:200]}")
            match = re.search(r"\{.*\}", clean_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            return {}


# Shared seller agent instance
seller_agent = SellerAgent()
