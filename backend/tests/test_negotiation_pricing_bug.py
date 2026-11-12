import sys
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env", override=True)

from app.models.seller import MerchantCommercialProfile, SellerRespondResponse
from app.models.negotiation import NegotiationStartRequest, NegotiationStartResponse
from app.agents.seller_agent import seller_agent
from app.agents.buyer_agent import buyer_agent
from app.services.negotiation_engine import negotiation_engine
from app.services.merchant_data import get_merchant_profile


class TestNegotiationPricingBug(unittest.IsolatedAsyncioTestCase):
    """
    Focused test suite verifying negotiation pricing constraints and bug fixes:
    1. Seller counteroffer never exceeds advertised/listed price.
    2. Buyer offer/counteroffer never exceeds buyer max acceptable price.
    3. Seller minimum acceptable price protection (never accept below floor).
    4. Delivery charges are kept strictly separate from product price.
    5. No mutually acceptable deal (ZOPA failure returns negotiation_failed).
    6. Successful deal within both agents' constraints.
    """

    def setUp(self):
        # Product advertised at $159, with seller floor at $135
        self.merchant = MerchantCommercialProfile(
            merchant_id="merchant-aurora",
            merchant_name="Aurora Official Store",
            product_id="prod-smartwatch",
            listed_price=159.0,
            minimum_acceptable_price=135.0,
            available_inventory=10,
            maximum_permitted_discount=24.0,
            delivery_cost=15.0,
            free_delivery_allowed=False,
            promotional_rules=["Free express delivery not included for discounted items."]
        )

    def test_case_1_seller_counteroffer_above_listed_price(self):
        """
        Test 1: Seller counteroffer above listed price.
        Verifies that when Gemini generates a rogue counteroffer ($175.0) that exceeds
        the advertised/listed price ($159.0), Python enforcement strictly clamps
        the counteroffer to <= $159.0 and sanitizes the customer-facing message.
        """
        rogue_seller_output = {
            "status": "counter_offer",
            "offered_price": 175.0,  # Rogue price exceeding $159 listed price
            "delivery": "paid ($15.00)",
            "reasoning": "Rogue pricing logic trying to counter above list price",
            "conditions": [],
            "message": "I can offer $175.00 plus $15.00 delivery fee."
        }

        result = seller_agent._enforce_deterministic_constraints(
            raw_proposal=rogue_seller_output,
            buyer_price=115.0,
            buyer_delivery="Free standard delivery",
            product_name="Smartwatch Pro",
            merchant=self.merchant
        )

        self.assertEqual(result.status, "counter_offer")
        self.assertIsNotNone(result.offered_price)
        self.assertLessEqual(
            result.offered_price,
            self.merchant.listed_price,
            f"Seller counteroffer ({result.offered_price}) MUST NOT exceed listed price ({self.merchant.listed_price})"
        )
        self.assertGreaterEqual(
            result.offered_price,
            self.merchant.minimum_acceptable_price,
            f"Seller counteroffer ({result.offered_price}) MUST be >= minimum acceptable price ({self.merchant.minimum_acceptable_price})"
        )
        # Message must also be sanitized (no $175)
        self.assertNotIn("$175", result.message)
        print("✓ Test 1 passed: Seller counteroffer above listed price clamped and message sanitized.")

    def test_case_2_buyer_offer_above_maximum_price(self):
        """
        Test 2: Buyer offer above maximum price.
        Verifies that when Gemini generates a buyer counteroffer or acceptance exceeding
        the buyer's max budget ($150.0), Python enforcement blocks acceptance and clamps
        the offer to <= max_price ($150.0).
        """
        rogue_buyer_output = {
            "status": "accepted",
            "counter_price": 165.0,
            "reasoning": "Rogue acceptance above buyer ceiling",
            "message": "I can accept $165.00."
        }

        result = buyer_agent._enforce_deterministic_constraints(
            parsed_proposal=rogue_buyer_output,
            seller_offered_price=165.0,  # Exceeds buyer max budget of $150.0
            seller_delivery="paid ($15.00)",
            target_price=129.0,
            max_price=150.0,
            previous_buyer_offer=115.0,
            round_number=2,
            max_rounds=5,
            delivery_preference="Free standard delivery",
            advertised_price=159.0
        )

        self.assertNotEqual(
            result["status"],
            "accepted",
            "Buyer agent MUST NOT accept an offer above customer maximum price ceiling!"
        )
        if result["status"] == "counter_offer":
            self.assertLessEqual(
                result["proposed_price"],
                150.0,
                f"Buyer counteroffer ({result['proposed_price']}) MUST NOT exceed max_price (150.0)"
            )
        self.assertNotIn("$165", result["message"])
        print("✓ Test 2 passed: Buyer offer above max price blocked and clamped.")

    def test_case_3_seller_minimum_acceptable_price_protection(self):
        """
        Test 3: Seller minimum acceptable price protection.
        Verifies that the seller can NEVER accept an offer below its minimum price floor ($135.0).
        """
        rogue_seller_accept = {
            "status": "accepted",
            "offered_price": 115.0,  # Below $135 minimum acceptable price
            "delivery": "free",
            "reasoning": "Rogue acceptance below cost floor",
            "conditions": [],
            "message": "We accept your offer of $115.00."
        }

        result = seller_agent._enforce_deterministic_constraints(
            raw_proposal=rogue_seller_accept,
            buyer_price=115.0,
            buyer_delivery="free",
            product_name="Smartwatch Pro",
            merchant=self.merchant
        )

        self.assertNotEqual(
            result.status,
            "accepted",
            "Seller agent MUST NOT accept an offer below minimum acceptable price!"
        )
        self.assertGreaterEqual(
            result.offered_price,
            self.merchant.minimum_acceptable_price,
            f"Seller counteroffer ({result.offered_price}) must be >= minimum acceptable price ({self.merchant.minimum_acceptable_price})"
        )
        print("✓ Test 3 passed: Seller minimum acceptable price protection verified.")

    def test_case_4_delivery_charges_kept_separate(self):
        """
        Test 4: Delivery charges separation.
        Verifies that product price and delivery charges are strictly decoupled:
        a $15 delivery fee must live in delivery/conditions, and must NOT inflate
        the product price beyond listed price.
        """
        raw_seller_output = {
            "status": "counter_offer",
            "offered_price": 150.0,
            "delivery": "paid ($15.00)",
            "reasoning": "Product discounted to $150 with $15 shipping fee",
            "conditions": ["Standard shipping fee of $15.00 applies"],
            "message": "I can offer $150.00 plus $15.00 delivery fee."
        }

        result = seller_agent._enforce_deterministic_constraints(
            raw_proposal=raw_seller_output,
            buyer_price=125.0,
            buyer_delivery="Free standard delivery",
            product_name="Smartwatch Pro",
            merchant=self.merchant
        )

        self.assertEqual(result.offered_price, 150.0)
        self.assertIn("15.00", result.delivery)
        # Verify offered_price is strictly item price, does NOT roll in 150 + 15 = 165
        self.assertLessEqual(result.offered_price, self.merchant.listed_price)
        print("✓ Test 4 passed: Delivery charges are kept strictly separate from product price.")

    async def test_case_5_no_mutually_acceptable_deal_zopa_failure(self):
        """
        Test 5: No mutually acceptable deal (ZOPA failure).
        Buyer max budget: $120.0
        Seller minimum floor: $135.0
        No overlap exists. Negotiation MUST result in negotiation_failed (never fabricate a deal).
        """
        req = NegotiationStartRequest(
            product_id="prod-smartwatch",
            product_name="Smartwatch Pro",
            merchant_name="Aurora Official Store",
            advertised_price=159.0,
            target_price=110.0,
            max_price=120.0,  # Buyer ceiling $120 < Seller floor $135
            max_rounds=2,
            merchant_constraints=self.merchant
        )

        resp = await negotiation_engine.negotiate(req)

        self.assertIsNone(resp.final_agreed_price, "No deal price should be agreed when ZOPA is empty!")
        self.assertEqual(
            resp.status,
            "negotiation_failed",
            f"Expected negotiation_failed when no overlap exists, got: {resp.status}"
        )
        print("✓ Test 5 passed: ZOPA failure correctly terminates as negotiation_failed.")

    async def test_case_6_successful_deal_within_both_constraints(self):
        """
        Test 6: Successful deal within both agents' constraints.
        Listed: $159.0
        Buyer target: $129.0, Buyer max: $159.0
        Seller floor: $135.0
        Valid ZOPA: [$135.0, $159.0].
        Simulated multi-round convergence within constraints.
        """
        # Mock Gemini to simulate realistic offers
        mock_buyer_plan = AsyncMock()
        mock_buyer_plan.opening_offer = 115.0
        mock_buyer_plan.delivery_conditions = "Free standard delivery"
        mock_buyer_plan.strategy = "Anchored at $115 with $159 ceiling"

        req = NegotiationStartRequest(
            product_id="prod-smartwatch",
            product_name="Smartwatch Pro",
            merchant_name="Aurora Official Store",
            advertised_price=159.0,
            target_price=129.0,
            max_price=159.0,
            max_rounds=3,
            merchant_constraints=self.merchant
        )

        with patch("app.agents.buyer_agent.buyer_agent.prepare_negotiation_plan", return_value=mock_buyer_plan):
            # In round 1, seller counters at $145
            seller_round_1 = SellerRespondResponse(
                status="counter_offer",
                offered_price=145.0,
                delivery="paid ($15.00)",
                reasoning="Countering at $145.00 with shipping fee",
                conditions=["Standard shipping fee applies"],
                message="I can offer $145.00 plus $15.00 delivery fee."
            )
            # In round 2, buyer accepts $145
            buyer_round_2 = {
                "status": "accepted",
                "proposed_price": 145.0,
                "delivery_conditions": "paid ($15.00)",
                "reasoning": "Price $145 is within customer max budget of $159",
                "message": "We accept your offer of $145.00."
            }

            with patch("app.agents.seller_agent.seller_agent.evaluate_buyer_proposal", return_value=seller_round_1):
                with patch("app.agents.buyer_agent.buyer_agent.evaluate_seller_counteroffer", return_value=buyer_round_2):
                    resp = await negotiation_engine.negotiate(req)

        self.assertEqual(resp.status, "deal_reached")
        self.assertEqual(resp.final_agreed_price, 145.0)
        self.assertLessEqual(resp.final_agreed_price, req.advertised_price)
        self.assertLessEqual(resp.final_agreed_price, req.max_price)
        self.assertGreaterEqual(resp.final_agreed_price, self.merchant.minimum_acceptable_price)
        print(f"✓ Test 6 passed: Successful deal reached at ${resp.final_agreed_price} within both agents' constraints.")


if __name__ == "__main__":
    unittest.main()
