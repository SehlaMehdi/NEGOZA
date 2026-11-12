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
from app.models.negotiation import NegotiationStartRequest
from app.agents.seller_agent import seller_agent
from app.agents.buyer_agent import buyer_agent
from app.services.negotiation_engine import negotiation_engine


class TestSellerNegotiationIntelligence(unittest.IsolatedAsyncioTestCase):
    """
    Test suite verifying enhanced Seller Agent negotiation intelligence:
    1. Seller rejecting/countering an opening offer below its preferred price.
    2. Seller making a meaningful counteroffer.
    3. Seller progressively conceding across negotiation rounds.
    4. Seller accepting an offer within its configured acceptance strategy.
    5. Seller refusing/countering offers below its minimum price floor.
    6. Successful middle-ground agreement reached between buyer and seller.
    7. Negotiation failure when no agreement is possible (empty ZOPA).
    """

    def setUp(self):
        # Product listed at $159: Preferred $145, Floor $125
        self.merchant = MerchantCommercialProfile(
            merchant_id="merchant-aurora",
            merchant_name="Aurora Official Store",
            product_id="prod-smartwatch",
            listed_price=159.0,
            preferred_price=145.0,
            minimum_acceptable_price=125.0,
            available_inventory=10,
            maximum_permitted_discount=34.0,
            delivery_cost=15.0,
            free_delivery_allowed=True,
            promotional_rules=["Standard promotional policy applies."]
        )

    def test_1_seller_counters_opening_offer_below_preferred_price(self):
        """
        Scenario 1: Opening offer below preferred price.
        Buyer offers $130 (which is above floor $125, but below preferred $145).
        Even if Gemini carelessly says 'accepted', Python enforcement must override
        to 'counter_offer' in round 1 to protect the merchant's commercial margin.
        """
        raw_seller_output = {
            "status": "accepted",
            "offered_price": 130.0,
            "delivery": "free",
            "reasoning": "Premature acceptance of opening offer below target margin",
            "conditions": [],
            "message": "We accept your opening offer of $130.00."
        }

        result = seller_agent._enforce_deterministic_constraints(
            raw_proposal=raw_seller_output,
            buyer_price=130.0,
            buyer_delivery="free",
            product_name="Smartwatch Pro",
            merchant=self.merchant,
            round_number=1,
            previous_context=None
        )

        self.assertEqual(
            result.status,
            "counter_offer",
            "Seller Agent MUST NOT accept an opening offer below its preferred price in Round 1!"
        )
        self.assertGreaterEqual(
            result.offered_price,
            self.merchant.preferred_price,
            f"Seller counteroffer ({result.offered_price}) should protect preferred margin (${self.merchant.preferred_price})"
        )
        self.assertLessEqual(
            result.offered_price,
            self.merchant.listed_price,
            f"Seller counteroffer ({result.offered_price}) must not exceed list price (${self.merchant.listed_price})"
        )
        print("✓ Test 1 passed: Seller countered opening offer below preferred price.")

    def test_2_seller_makes_meaningful_counteroffer(self):
        """
        Scenario 2: Meaningful counteroffer.
        Buyer offers $115 (below min $125).
        Seller must formulate a meaningful counteroffer near or above preferred price ($145),
        and not collapse straight down to the minimum acceptable price ($125).
        """
        raw_seller_output = {
            "status": "counter_offer",
            "offered_price": 150.0,
            "delivery": "free",
            "reasoning": "Countering near list price to test buyer willingness to pay",
            "conditions": [],
            "message": "I can offer $150.00 with free delivery."
        }

        result = seller_agent._enforce_deterministic_constraints(
            raw_proposal=raw_seller_output,
            buyer_price=115.0,
            buyer_delivery="free",
            product_name="Smartwatch Pro",
            merchant=self.merchant,
            round_number=1,
            previous_context=None
        )

        self.assertEqual(result.status, "counter_offer")
        self.assertGreater(result.offered_price, self.merchant.minimum_acceptable_price)
        self.assertLessEqual(result.offered_price, self.merchant.listed_price)
        self.assertEqual(result.offered_price, 150.0)
        print("✓ Test 2 passed: Seller formulated a meaningful counteroffer ($150.0).")

    def test_3_seller_progressively_conceding(self):
        """
        Scenario 3: Progressive concessions.
        Round 1: Buyer offers $115 -> Seller counteroffers $150.
        Round 2: Buyer counters $128 -> Seller counteroffers $144 (conceding).
        Round 3: Buyer counters $135 -> Seller counteroffers $138 (conceding further).
        Verify monotonic concession: $150 > $144 > $138 >= $125.
        Also verifies Python enforces seller cannot raise counteroffer.
        """
        # Round 1 context
        context_r1 = [
            {"round": 1, "agent": "buyer", "price": 115.0, "message": "Offer $115"},
            {"round": 1, "agent": "seller", "price": 150.0, "message": "Counter $150"}
        ]

        # In Round 2, suppose seller proposes $144
        res_r2 = seller_agent._enforce_deterministic_constraints(
            raw_proposal={"status": "counter_offer", "offered_price": 144.0, "delivery": "free", "message": "I can offer $144.00."},
            buyer_price=128.0,
            buyer_delivery="free",
            product_name="Smartwatch Pro",
            merchant=self.merchant,
            round_number=2,
            previous_context=context_r1
        )
        self.assertEqual(res_r2.status, "counter_offer")
        self.assertLess(res_r2.offered_price, 150.0, "Seller counteroffer must concede from Round 1 ($150.0)")

        # Round 2 context
        context_r2 = context_r1 + [
            {"round": 2, "agent": "buyer", "price": 128.0, "message": "Offer $128"},
            {"round": 2, "agent": "seller", "price": 144.0, "message": "Counter $144"}
        ]

        # In Round 3, suppose seller proposes $138
        res_r3 = seller_agent._enforce_deterministic_constraints(
            raw_proposal={"status": "counter_offer", "offered_price": 138.0, "delivery": "free", "message": "I can offer $138.00."},
            buyer_price=135.0,
            buyer_delivery="free",
            product_name="Smartwatch Pro",
            merchant=self.merchant,
            round_number=3,
            previous_context=context_r2
        )
        self.assertEqual(res_r3.status, "counter_offer")
        self.assertLess(res_r3.offered_price, 144.0, "Seller counteroffer must concede from Round 2 ($144.0)")
        self.assertGreaterEqual(res_r3.offered_price, self.merchant.minimum_acceptable_price)

        # Test regression protection: if AI tried to counter with $155 in Round 3, Python clamps it
        res_rogue = seller_agent._enforce_deterministic_constraints(
            raw_proposal={"status": "counter_offer", "offered_price": 155.0, "delivery": "free", "message": "I can offer $155.00."},
            buyer_price=135.0,
            buyer_delivery="free",
            product_name="Smartwatch Pro",
            merchant=self.merchant,
            round_number=3,
            previous_context=context_r2
        )
        self.assertLessEqual(res_rogue.offered_price, 144.0, "Seller cannot increase counteroffer above previous offer ($144.0)")
        print("✓ Test 3 passed: Seller progressively conceded across rounds ($150 -> $144 -> $138).")

    def test_4_seller_accepting_offer_within_acceptance_strategy(self):
        """
        Scenario 4: Acceptance within strategy.
        Case 4A: Buyer offers $146 (>= preferred $145).
        Seller immediately accepts.
        Case 4B: Later round (Round 3) where buyer offers $138 (> min $125) after negotiation.
        Seller accepts the mutually converged compromise.
        """
        # Case 4A: Above preferred price
        res_4a = seller_agent._enforce_deterministic_constraints(
            raw_proposal={"status": "accepted", "offered_price": 146.0, "delivery": "free", "message": "We accept $146.00."},
            buyer_price=146.0,
            buyer_delivery="free",
            product_name="Smartwatch Pro",
            merchant=self.merchant,
            round_number=1,
            previous_context=None
        )
        self.assertEqual(res_4a.status, "accepted")
        self.assertEqual(res_4a.offered_price, 146.0)

        # Case 4B: Round 3 compromise acceptance above min price floor
        context_r2 = [
            {"round": 1, "agent": "buyer", "price": 115.0},
            {"round": 1, "agent": "seller", "price": 150.0},
            {"round": 2, "agent": "buyer", "price": 130.0},
            {"round": 2, "agent": "seller", "price": 142.0}
        ]
        res_4b = seller_agent._enforce_deterministic_constraints(
            raw_proposal={"status": "accepted", "offered_price": 138.0, "delivery": "free", "message": "We accept $138.00."},
            buyer_price=138.0,
            buyer_delivery="free",
            product_name="Smartwatch Pro",
            merchant=self.merchant,
            round_number=3,
            previous_context=context_r2
        )
        self.assertEqual(res_4b.status, "accepted")
        self.assertEqual(res_4b.offered_price, 138.0)
        print("✓ Test 4 passed: Seller accepted offers within configured acceptance strategy.")

    def test_5_seller_refuses_offers_below_minimum(self):
        """
        Scenario 5: Refusal below minimum floor.
        Buyer offers $105 (< min $125).
        Even if AI hallucinates 'accepted', Python strictly overrides to 'counter_offer'.
        Offered price is strictly >= $125.
        """
        raw_rogue = {
            "status": "accepted",
            "offered_price": 105.0,
            "delivery": "free",
            "message": "We accept $105.00."
        }
        res = seller_agent._enforce_deterministic_constraints(
            raw_proposal=raw_rogue,
            buyer_price=105.0,
            buyer_delivery="free",
            product_name="Smartwatch Pro",
            merchant=self.merchant,
            round_number=2,
            previous_context=[]
        )
        self.assertNotEqual(res.status, "accepted")
        self.assertGreaterEqual(res.offered_price, self.merchant.minimum_acceptable_price)
        print("✓ Test 5 passed: Seller strictly refused/countered offer below minimum acceptable floor.")

    async def test_6_successful_middle_ground_agreement(self):
        """
        Scenario 6: Successful middle-ground agreement.
        Listed: $159, Preferred: $145, Floor: $125.
        Buyer: Target $129, Max budget: $159.
        Multi-round simulated bargaining converges to a fair middle ground ($138.0).
        """
        mock_buyer_plan = AsyncMock()
        mock_buyer_plan.opening_offer = 115.0
        mock_buyer_plan.delivery_conditions = "Free standard delivery"
        mock_buyer_plan.strategy = "Opening bid at $115"

        req = NegotiationStartRequest(
            product_id="prod-smartwatch",
            product_name="Smartwatch Pro",
            merchant_name="Aurora Official Store",
            advertised_price=159.0,
            target_price=129.0,
            max_price=159.0,
            max_rounds=4,
            merchant_constraints=self.merchant
        )

        with patch("app.agents.buyer_agent.buyer_agent.prepare_negotiation_plan", return_value=mock_buyer_plan):
            # Round 1: Seller counters at $148
            seller_r1 = SellerRespondResponse(
                status="counter_offer", offered_price=148.0, delivery="free",
                reasoning="Anchoring near preferred price", conditions=[], message="I can offer $148.00 with free delivery."
            )
            # Round 2: Buyer counters $128
            buyer_r2 = {
                "status": "counter_offer", "proposed_price": 128.0, "delivery_conditions": "free",
                "reasoning": "Conceding towards target", "message": "We can counter with $128.00."
            }
            # Round 2: Seller counters $140
            seller_r2 = SellerRespondResponse(
                status="counter_offer", offered_price=140.0, delivery="free",
                reasoning="Conceding towards middle ground", conditions=[], message="I can meet at $140.00."
            )
            # Round 3: Buyer counters $138
            buyer_r3 = {
                "status": "counter_offer", "proposed_price": 138.0, "delivery_conditions": "free",
                "reasoning": "Close to middle ground", "message": "Can we agree on $138.00?"
            }
            # Round 3: Seller accepts $138
            seller_r3 = SellerRespondResponse(
                status="accepted", offered_price=138.0, delivery="free",
                reasoning="Mutually acceptable middle ground achieved in Round 3", conditions=[], message="We accept $138.00 with free delivery."
            )

            with patch("app.agents.seller_agent.seller_agent.evaluate_buyer_proposal", side_effect=[seller_r1, seller_r2, seller_r3]):
                with patch("app.agents.buyer_agent.buyer_agent.evaluate_seller_counteroffer", side_effect=[buyer_r2, buyer_r3]):
                    resp = await negotiation_engine.negotiate(req)

        self.assertEqual(resp.status, "deal_reached")
        self.assertEqual(resp.final_agreed_price, 138.0)
        self.assertEqual(resp.rounds_count, 3)
        self.assertGreaterEqual(resp.final_agreed_price, self.merchant.minimum_acceptable_price)
        self.assertLessEqual(resp.final_agreed_price, self.merchant.listed_price)
        print(f"✓ Test 6 passed: Successful middle-ground agreement reached at ${resp.final_agreed_price} in Round 3.")

    async def test_7_negotiation_failure_when_no_agreement_possible(self):
        """
        Scenario 7: Negotiation failure (ZOPA failure).
        Buyer maximum budget: $115.
        Seller minimum floor: $125.
        No overlap exists. Must conclude as negotiation_failed.
        """
        req = NegotiationStartRequest(
            product_id="prod-smartwatch",
            product_name="Smartwatch Pro",
            merchant_name="Aurora Official Store",
            advertised_price=159.0,
            target_price=100.0,
            max_price=115.0,  # Below seller floor of $125
            max_rounds=2,
            merchant_constraints=self.merchant
        )

        resp = await negotiation_engine.negotiate(req)

        self.assertEqual(resp.status, "negotiation_failed")
        self.assertIsNone(resp.final_agreed_price)
        self.assertTrue(len(resp.transcript) >= 2)
        print("✓ Test 7 passed: Negotiation failure correctly returned when no agreement is possible.")


if __name__ == "__main__":
    unittest.main()
