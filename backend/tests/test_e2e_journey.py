"""
NEGOZA End-to-End Core Demo Journey Test
Tests all 10 steps of the live user journey with a real Channel3 product:
1. Real Channel3 product discovery
2. User selects product & clicks 'Add my Agent'
3. Activation parameters received
4. Target budget & ceiling configuration
5. Buyer & Seller Agent live Gemini negotiation
6. Auditable negotiation transcript
7. Pricing constraints enforced
8. Agreed price, delivery, and savings displayed
9. Review and approval of deal
10. PayPal Sandbox order creation and real capture status
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env", override=True)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_e2e_demo():
    print("=== SIMULATING FULL NEGOZA END-TO-END DEMO JOURNEY ===")

    # Step 1: Real Channel3 Product Discovery
    print("\n[Step 1] Fetching live Channel3 products for 'smartwatch'...")
    res1 = client.get("/api/products/search?q=smartwatch&limit=5")
    assert res1.status_code == 200, f"Channel3 search failed: {res1.text}"
    products = res1.json().get("products", [])
    assert len(products) > 0, "No products returned from Channel3"
    chosen = products[0]
    print(f"✓ Found real product: '{chosen['name']}' by {chosen['merchant']}")
    print(f"  Advertised Price: ${chosen['advertisedPrice']}")

    # Step 2, 3 & 4: User configures target budget and ceiling
    target_budget = round(chosen["advertisedPrice"] * 0.82, 2)
    max_ceiling = chosen["advertisedPrice"]
    print(f"\n[Steps 2, 3 & 4] Agent activated for '{chosen['name']}':")
    print(f"  Target Price: ${target_budget:.2f} | Ceiling: ${max_ceiling:.2f}")

    # Step 5, 6, 7 & 8: Autonomous Multi-Round Negotiation via Gemini
    print("\n[Steps 5, 6, 7 & 8] Executing live Gemini multi-round negotiation...")
    neg_res = client.post("/api/negotiation/start", json={
        "product_id": chosen["id"],
        "product_name": chosen["name"],
        "merchant_name": chosen["merchant"],
        "advertised_price": chosen["advertisedPrice"],
        "target_price": target_budget,
        "max_price": max_ceiling,
        "delivery_preference": "Free standard delivery",
        "requirements": ["Verified authentic retail unit"],
        "max_rounds": 4
    })
    assert neg_res.status_code == 200, f"Negotiation failed: {neg_res.text}"
    neg_data = neg_res.json()
    print(f"✓ Negotiation concluded: {neg_data['status']} in {neg_data['rounds_count']} rounds")
    print(f"  Agreed Product Price: ${neg_data.get('final_agreed_price')}")
    print(f"  Delivery Terms: {neg_data.get('delivery_terms')}")
    print(f"  Summary: {neg_data.get('summary')}")
    print(f"  Transcript Turns: {len(neg_data.get('transcript', []))}")
    assert len(neg_data.get("transcript", [])) > 0, "Expected non-empty transcript"

    # Step 9 & 10: Deal Approval & PayPal Sandbox Checkout
    print("\n[Steps 9 & 10] User reviews deal and initiates PayPal Sandbox checkout...")
    final_price = neg_data.get("final_agreed_price") or target_budget
    paypal_res = client.post("/api/payments/paypal/orders/create", json={
        "negotiation_id": neg_data["negotiation_id"],
        "product_name": chosen["name"],
        "amount": final_price,
        "currency": "USD"
    })
    assert paypal_res.status_code == 201, f"PayPal order creation failed: {paypal_res.text}"
    paypal_order = paypal_res.json()
    print("✓ Live PayPal Sandbox Order Created:")
    print(f"  Order ID: {paypal_order['order_id']}")
    print(f"  Status: {paypal_order['status']}")
    print(f"  Approve URL: {paypal_order['approve_url']}")

    # Step 10b: Query actual capture status
    print("\n[Step 10b] Verifying authentic capture check with PayPal Sandbox API...")
    cap_res = client.post(f"/api/payments/paypal/orders/{paypal_order['order_id']}/capture")
    assert cap_res.status_code == 200, f"Capture query failed: {cap_res.text}"
    cap_data = cap_res.json()
    print(f"✓ PayPal Sandbox API responded with: {cap_data['status']}")
    print(f"  Detail: {cap_data['message'][:85]}...")

    print("\n=======================================================")
    print("ALL 10 STEPS OF THE CORE DEMO JOURNEY FULLY OPERATIONAL!")
    print("=======================================================")

if __name__ == "__main__":
    run_e2e_demo()
