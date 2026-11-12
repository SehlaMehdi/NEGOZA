import sys
import time
from pathlib import Path
from unittest.mock import patch

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env", override=True)

from fastapi.testclient import TestClient
from app.main import app
from app.models.seller import MerchantCommercialProfile
from app.agents.buyer_agent import buyer_agent
from app.agents.seller_agent import seller_agent

client = TestClient(app)


def test_case_6_buyer_maximum_price_protection():
    """
    Test 6: Buyer Maximum-Price Protection.
    Verifies that Python deterministic enforcement strictly blocks any Buyer offer
    or acceptance that exceeds the user's maximum price ceiling.
    """
    # Rogue AI simulation: AI tries to accept $275 or counter at $280 when max_price is $250
    rogue_parsed = {
        "status": "accepted",
        "counter_price": 280.0,
        "reasoning": "Rogue acceptance above ceiling",
        "message": "I accept $275"
    }

    result = buyer_agent._enforce_deterministic_constraints(
        parsed_proposal=rogue_parsed,
        seller_offered_price=275.0,  # Exceeds max_price ($250.0)
        seller_delivery="Free standard delivery",
        target_price=230.0,
        max_price=250.0,  # Hard ceiling
        previous_buyer_offer=220.0,
        round_number=1,
        max_rounds=5,
        delivery_preference="Free standard delivery"
    )

    # Python MUST override: cannot accept an offer above $250
    assert result["status"] != "accepted", "Buyer Agent Python validation MUST NOT allow acceptance above max_price!"
    if result["status"] == "counter_offer":
        assert result["proposed_price"] <= 250.0, f"Buyer offer (${result['proposed_price']}) cannot exceed max_price ($250.0)!"


def test_case_7_seller_minimum_price_protection():
    """
    Test 7: Seller Minimum-Price Protection.
    Verifies that Python deterministic enforcement strictly blocks any Seller offer
    or acceptance below the merchant's configured minimum acceptable price.
    """
    merchant = MerchantCommercialProfile(
        merchant_id="merchant-chronos",
        merchant_name="Chronos Official",
        product_id="prod-1",
        listed_price=299.0,
        minimum_acceptable_price=235.0,  # Floor is $235
        available_inventory=10,
        maximum_permitted_discount=64.0,
        delivery_cost=15.0,
        free_delivery_allowed=True,
        promotional_rules=[]
    )

    # Rogue AI simulation: AI accepted $190 or countered below $235 floor
    rogue_output = {
        "status": "accepted",
        "offered_price": 190.0,
        "delivery": "free",
        "reasoning": "Rogue discount",
        "conditions": [],
        "message": "I accept $190"
    }

    result = seller_agent._enforce_deterministic_constraints(
        raw_proposal=rogue_output,
        buyer_price=190.0,
        buyer_delivery="Free standard delivery",
        product_name="Aura Horizon Chrono Pro",
        merchant=merchant
    )

    assert result.status != "accepted", "Seller Agent Python validation MUST NOT accept offer below minimum floor!"
    if result.status == "counter_offer":
        assert result.offered_price >= 235.0, f"Seller counter-offer (${result.offered_price}) cannot be below minimum ($235.0)!"


def test_case_5_gemini_api_failure():
    """
    Test 5: Gemini API Failure Handling.
    Verifies that negotiation loop handles upstream AI exceptions gracefully,
    logs the event in the transcript, and returns structured 'negotiation_failed'
    without crashing or returning an unhandled 500 error.
    """
    with patch.object(
        buyer_agent.service,
        "generate_response",
        side_effect=RuntimeError("Simulated Gemini API quota exhaustion or network timeout")
    ):
        payload = {
            "product_id": "prod-1",
            "product_name": "Aura Horizon Chrono Pro",
            "advertised_price": 299.0,
            "target_price": 240.0,
            "max_price": 260.0
        }
        res = client.post("/api/negotiation/start", json=payload)
        assert res.status_code == 200, f"Expected 200 with structured failure, got: {res.text}"
        data = res.json()
        assert data["status"] == "negotiation_failed"
        assert data["final_agreed_price"] is None
        assert len(data["transcript"]) > 0


def test_case_1_successful_negotiation_api():
    """
    Test 1: Successful Negotiation via HTTP API.
    A realistic negotiation where Buyer target is $250 and max is $270
    on a $299 watch with merchant floor of $235.
    Both agents find mutual agreement.
    """
    payload = {
        "product_id": "prod-1",
        "product_name": "Aura Horizon Chrono Pro",
        "advertised_price": 299.0,
        "target_price": 250.0,
        "max_price": 270.0,
        "delivery_preference": "Free standard delivery",
        "max_rounds": 5
    }

    http_response = client.post("/api/negotiation/start", json=payload)
    assert http_response.status_code == 200, f"Expected 200 OK, got: {http_response.text}"

    data = http_response.json()
    assert "negotiation_id" in data
    assert data["product_id"] == "prod-1"
    assert data["status"] in ("deal_reached", "maximum_rounds_reached")
    
    if data["status"] == "deal_reached":
        assert data["final_agreed_price"] is not None
        assert data["final_agreed_price"] >= 235.0, "Agreed price cannot be below merchant floor ($235.0)"
        assert data["final_agreed_price"] <= 270.0, "Agreed price cannot exceed buyer ceiling ($270.0)"
        assert data["delivery_terms"] is not None
    
    assert len(data["transcript"]) >= 2
    for record in data["transcript"]:
        assert record["agent"] in ("buyer", "seller")
        assert "round_number" in record
        assert "action" in record
        assert "reasoning" in record
        assert "agent_response" in record


def test_case_2_seller_refusing_buyer_budget():
    """
    Test 2: Seller Refusing Buyer's Budget.
    Buyer's target and max price ($80) are far below merchant's minimum floor ($235).
    """
    payload = {
        "product_id": "prod-1",
        "product_name": "Aura Horizon Chrono Pro",
        "advertised_price": 299.0,
        "target_price": 60.0,
        "max_price": 80.0,
        "max_rounds": 2
    }

    res = client.post("/api/negotiation/start", json=payload)
    assert res.status_code == 200, f"Expected 200 OK, got: {res.text}"
    data = res.json()
    assert data["status"] in ("negotiation_failed", "maximum_rounds_reached")
    assert data["final_agreed_price"] is None
    assert len(data["transcript"]) > 0


def test_case_3_seller_reaching_minimum_price():
    """
    Test 3: Seller Reaching its Minimum Price.
    Merchant minimum is $235.0. Buyer target is $230, max is $240.
    Verifies that seller offers never go below $235.0.
    """
    payload = {
        "product_id": "prod-1",
        "product_name": "Aura Horizon Chrono Pro",
        "advertised_price": 299.0,
        "target_price": 230.0,
        "max_price": 240.0,
        "max_rounds": 2
    }

    res = client.post("/api/negotiation/start", json=payload)
    assert res.status_code == 200, f"Expected 200 OK, got: {res.text}"
    data = res.json()

    for turn in data["transcript"]:
        if turn["agent"] == "seller" and turn["proposed_price"] is not None:
            assert turn["proposed_price"] >= 235.0, (
                f"Seller proposed price (${turn['proposed_price']}) violated merchant minimum ($235.0)!"
            )


def test_case_4_maximum_rounds_reached():
    """
    Test 4: Maximum Rounds Reached.
    Tests when negotiation terminates gracefully upon hitting max_rounds.
    """
    payload = {
        "product_id": "prod-3",  # KicksLab sneakers, strict $150 floor, no free delivery
        "product_name": "Aerorush Vapor Runner",
        "advertised_price": 180.0,
        "target_price": 120.0,
        "max_price": 130.0,      # Incompatible spread: Buyer max $130 vs Seller min $150
        "max_rounds": 1          # 1 round cap
    }

    res = client.post("/api/negotiation/start", json=payload)
    assert res.status_code == 200, f"Expected 200 OK, got: {res.text}"
    data = res.json()
    assert data["status"] in ("maximum_rounds_reached", "negotiation_failed")
    assert data["final_agreed_price"] is None
    assert len(data["transcript"]) >= 1


if __name__ == "__main__":
    print("=== Running Negotiation Engine Test Suite ===")
    
    test_case_6_buyer_maximum_price_protection()
    print("✓ Test 6: Buyer Maximum-Price Protection passed.")
    
    test_case_7_seller_minimum_price_protection()
    print("✓ Test 7: Seller Minimum-Price Protection passed.")
    
    test_case_5_gemini_api_failure()
    print("✓ Test 5: Gemini API Failure Handling passed.")
    
    time.sleep(1)
    test_case_1_successful_negotiation_api()
    print("✓ Test 1: Successful Negotiation (Live Gemini + API) passed.")
    
    time.sleep(1)
    test_case_2_seller_refusing_buyer_budget()
    print("✓ Test 2: Seller Refusing Buyer Budget passed.")
    
    time.sleep(1)
    test_case_3_seller_reaching_minimum_price()
    print("✓ Test 3: Seller Reaching Minimum Price passed.")
    
    time.sleep(1)
    test_case_4_maximum_rounds_reached()
    print("✓ Test 4: Maximum Rounds Reached passed.")
    
    print("\nALL 7 NEGOTIATION ENGINE TESTS PASSED SUCCESSFULLY!")
