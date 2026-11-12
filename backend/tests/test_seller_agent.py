import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env", override=True)

from fastapi.testclient import TestClient
from app.main import app
from app.agents.seller_agent import seller_agent
from app.models.seller import MerchantCommercialProfile, SellerRespondResponse

client = TestClient(app)


def test_deterministic_python_enforcement_below_minimum():
    """
    Directly tests that Python deterministic enforcement overrides rogue AI output
    if Gemini erroneously accepts or offers a price below minimum_acceptable_price.
    """
    merchant = MerchantCommercialProfile(
        merchant_id="merchant-test",
        merchant_name="Test Merchant",
        product_id="prod-test",
        listed_price=300.0,
        minimum_acceptable_price=240.0,
        available_inventory=5,
        maximum_permitted_discount=60.0,
        delivery_cost=15.0,
        free_delivery_allowed=True,
        promotional_rules=[]
    )

    # Rogue AI simulation: AI accepted $180 (well below $240 minimum)
    rogue_ai_output = {
        "status": "accepted",
        "offered_price": 180.0,
        "delivery": "free",
        "reasoning": "Rogue acceptance below floor",
        "conditions": [],
        "message": "I accept $180"
    }

    result = seller_agent._enforce_deterministic_constraints(
        raw_proposal=rogue_ai_output,
        buyer_price=180.0,
        buyer_delivery="free",
        product_name="Test Product",
        merchant=merchant
    )

    # Invariant 1: Can NEVER be accepted below minimum acceptable price
    assert result.status != "accepted", "Python validation MUST reject or counter-offer when buyer offer is below minimum."
    # Invariant 2: Offered price must NEVER be below minimum acceptable price ($240)
    assert result.offered_price is not None and result.offered_price >= 240.0, (
        f"Python validation MUST enforce price floor ($240.0), got {result.offered_price}"
    )


def test_deterministic_python_enforcement_free_delivery_prohibited():
    """
    Directly tests that Python deterministic enforcement overrides rogue AI output
    if Gemini offers free delivery when merchant policy strictly forbids it.
    """
    merchant = MerchantCommercialProfile(
        merchant_id="merchant-test-strict",
        merchant_name="Strict Merchant",
        product_id="prod-strict",
        listed_price=180.0,
        minimum_acceptable_price=150.0,
        available_inventory=10,
        maximum_permitted_discount=30.0,
        delivery_cost=12.0,
        free_delivery_allowed=False,  # Free delivery forbidden
        promotional_rules=["Strict delivery surcharge: $12.00 applies"]
    )

    # Rogue AI simulation: AI promised free delivery
    rogue_ai_output = {
        "status": "counter_offer",
        "offered_price": 160.0,
        "delivery": "free",
        "reasoning": "I offer free delivery",
        "conditions": [],
        "message": "I can offer $160 with free delivery."
    }

    result = seller_agent._enforce_deterministic_constraints(
        raw_proposal=rogue_ai_output,
        buyer_price=155.0,
        buyer_delivery="free delivery requested",
        product_name="Strict Product",
        merchant=merchant
    )

    # Invariant: Delivery MUST NOT be free when merchant policy prohibits it
    assert "free" not in result.delivery.lower(), f"Free delivery prohibited, but got: {result.delivery}"
    assert "$12.00" in result.delivery or "paid" in result.delivery.lower()


def test_case_1_buyer_offer_above_merchant_minimum():
    """
    Case 1: Buyer offer ($270.0) above merchant minimum ($235.0) on a $299.0 item.
    """
    payload = {
        "product_id": "prod-1",
        "product_name": "Aura Horizon Chrono Pro",
        "buyer_proposed_price": 270.0,
        "delivery_conditions": "Free standard delivery"
    }

    response = client.post("/api/agents/seller/respond", json=payload)
    assert response.status_code == 200, f"Expected 200 OK, got: {response.text}"
    
    data = response.json()
    assert data["agent"] == "seller"
    assert data["status"] in ("accepted", "counter_offer")
    assert data["offered_price"] >= 235.0, "Offered price must be >= merchant minimum ($235.0)"
    assert data["offered_price"] <= 299.0, "Offered price must be <= list price ($299.0)"
    assert len(data["reasoning"]) > 0
    assert len(data["message"]) > 0


def test_case_2_buyer_offer_below_merchant_minimum():
    """
    Case 2: Buyer offer ($190.0) well below merchant minimum ($235.0) on a $299.0 item.
    Must generate a counter-offer >= minimum ($235.0) or reject. MUST NOT accept.
    """
    payload = {
        "product_id": "prod-1",
        "product_name": "Aura Horizon Chrono Pro",
        "buyer_proposed_price": 190.0,
        "delivery_conditions": "Free standard delivery"
    }

    response = client.post("/api/agents/seller/respond", json=payload)
    assert response.status_code == 200, f"Expected 200 OK, got: {response.text}"
    
    data = response.json()
    assert data["agent"] == "seller"
    assert data["status"] in ("counter_offer", "rejected"), "Status CANNOT be accepted when offer < minimum."
    
    if data["status"] == "counter_offer":
        assert data["offered_price"] >= 235.0, f"Counter offer (${data['offered_price']}) cannot be below minimum ($235.0)."
    else:
        assert data["offered_price"] is None


def test_case_3_buyer_offer_equal_to_merchant_minimum():
    """
    Case 3: Buyer offer ($235.0) exactly equal to merchant minimum ($235.0).
    """
    payload = {
        "product_id": "prod-1",
        "product_name": "Aura Horizon Chrono Pro",
        "buyer_proposed_price": 235.0,
        "delivery_conditions": "Free standard delivery"
    }

    response = client.post("/api/agents/seller/respond", json=payload)
    assert response.status_code == 200, f"Expected 200 OK, got: {response.text}"
    
    data = response.json()
    assert data["agent"] == "seller"
    assert data["status"] in ("accepted", "counter_offer")
    assert data["offered_price"] >= 235.0, "Offered price must be >= merchant minimum ($235.0)"


def test_case_4_free_delivery_allowed():
    """
    Case 4: Merchant permits free delivery (Product 1: Chronos Official, free_delivery_allowed=True).
    """
    payload = {
        "product_id": "prod-1",
        "product_name": "Aura Horizon Chrono Pro",
        "buyer_proposed_price": 275.0,
        "delivery_conditions": "Free standard delivery"
    }

    response = client.post("/api/agents/seller/respond", json=payload)
    assert response.status_code == 200, f"Expected 200 OK, got: {response.text}"
    
    data = response.json()
    assert data["agent"] == "seller"
    # When free delivery is permitted and offer is strong ($275 on a $299 item), delivery should be 'free'
    assert "free" in data["delivery"].lower(), f"Expected free delivery, got: {data['delivery']}"


def test_case_5_free_delivery_not_allowed():
    """
    Case 5: Merchant policy forbids free delivery (Product 3: KicksLab Sneakers, free_delivery_allowed=False, fee=$12).
    Buyer requests 'Free standard delivery', but merchant policy forces paid shipping.
    """
    payload = {
        "product_id": "prod-3",
        "product_name": "Aerorush Vapor Runner",
        "buyer_proposed_price": 165.0,
        "delivery_conditions": "Free standard delivery"
    }

    response = client.post("/api/agents/seller/respond", json=payload)
    assert response.status_code == 200, f"Expected 200 OK, got: {response.text}"
    
    data = response.json()
    assert data["agent"] == "seller"
    # Delivery must NOT be free because merchant.free_delivery_allowed is False
    assert "free" not in data["delivery"].lower(), f"Delivery should not be free: {data['delivery']}"
    assert "$12.00" in data["delivery"] or "paid" in data["delivery"].lower()


import time

if __name__ == "__main__":
    print("Running Seller Agent Test Suite...")
    test_deterministic_python_enforcement_below_minimum()
    print("✓ Deterministic Python enforcement (below minimum floor) passed.")
    test_deterministic_python_enforcement_free_delivery_prohibited()
    print("✓ Deterministic Python enforcement (free delivery prohibited) passed.")
    test_case_1_buyer_offer_above_merchant_minimum()
    print("✓ Case 1: Buyer offer above merchant minimum passed.")
    time.sleep(1)
    test_case_2_buyer_offer_below_merchant_minimum()
    print("✓ Case 2: Buyer offer below merchant minimum passed.")
    time.sleep(1)
    test_case_3_buyer_offer_equal_to_merchant_minimum()
    print("✓ Case 3: Buyer offer equal to merchant minimum passed.")
    time.sleep(1)
    test_case_4_free_delivery_allowed()
    print("✓ Case 4: Free delivery allowed passed.")
    time.sleep(1)
    test_case_5_free_delivery_not_allowed()
    print("✓ Case 5: Free delivery not allowed passed.")
    print("\nALL SELLER AGENT TESTS PASSED SUCCESSFULLY!")
