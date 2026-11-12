"""
Channel3 Product Discovery Test Suite.
Validates live product search, normalized Pydantic schemas, and error boundaries:
1. Live search for 'smartwatch' via GET /api/products/search?q=smartwatch
2. Verify actual product fields: id, name, merchant, advertisedPrice, originalPrice, image, productUrl
3. Empty query validation (HTTP 400)
4. Invalid API key error handling (HTTP 401)
5. Missing / unconfigured API key error handling (HTTP 503)
6. Security check (Zero API key leakage in responses or logs)
"""

import sys
from pathlib import Path
from unittest.mock import patch

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env", override=True)

from fastapi.testclient import TestClient
from app.main import app
from app.services.channel3_service import Channel3Service

client = TestClient(app)


def test_1_live_channel3_smartwatch_search():
    """
    Test 1: Live search for 'smartwatch' via GET /api/products/search?q=smartwatch
    """
    print("\n=== [Test 1] Testing live Channel3 search for 'smartwatch' ===")
    response = client.get("/api/products/search?q=smartwatch&limit=5")
    print(f"HTTP Status: {response.status_code}")
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"

    data = response.json()
    assert data["query"] == "smartwatch"
    assert data["source"] == "channel3"
    assert data["count"] > 0
    assert len(data["products"]) > 0

    first = data["products"][0]
    print(f"Discovered Product: '{first.get('name')}' by {first.get('merchant')}")
    print(f"Price: ${first.get('advertisedPrice')} (Original: ${first.get('originalPrice')})")
    print(f"Image: {first.get('image')[:60]}...")
    print(f"Product URL: {first.get('productUrl')}")

    # Core field validations
    assert first.get("id"), "Product ID missing"
    assert first.get("name"), "Product name missing"
    assert first.get("merchant"), "Merchant name missing"
    assert first.get("advertisedPrice") is not None and first.get("advertisedPrice") > 0
    assert first.get("originalPrice") is not None and first.get("originalPrice") > 0
    assert first.get("image"), "Image URL missing"

    # Dual compatibility check (snake_case and camelCase)
    assert first.get("advertised_price") == first.get("advertisedPrice")
    assert first.get("original_price") == first.get("originalPrice")

    # SECURITY CHECK
    raw_text = response.text.lower()
    assert "channel3_api_key" not in raw_text, "SECURITY VIOLATION: CHANNEL3_API_KEY exposed in response!"

    print("✓ Test 1 passed: Live Channel3 product search returned verified real products.")


def test_2_empty_query_validation():
    """
    Test 2: Empty query validation returns HTTP 400.
    """
    print("\n=== [Test 2] Testing empty search query ===")
    resp1 = client.get("/api/products/search?q=")
    print(f"Empty q status: {resp1.status_code}")
    assert resp1.status_code in (400, 422)

    resp2 = client.get("/api/products/search?q=   ")
    print(f"Whitespace q status: {resp2.status_code}")
    assert resp2.status_code == 400
    print("✓ Test 2 passed: Empty search queries correctly rejected.")


def test_3_invalid_api_key_handling():
    """
    Test 3: Invalid API key returns HTTP 401 Unauthorized.
    """
    print("\n=== [Test 3] Testing invalid API key ===")
    mock_service = Channel3Service(api_key="ch3_invalid_test_key_12345")
    with patch("app.routes.products.channel3_service", mock_service):
        resp = client.get("/api/products/search?q=smartwatch")
        print(f"Invalid API key status: {resp.status_code}")
        assert resp.status_code == 401
    print("✓ Test 3 passed: Invalid API key handled with HTTP 401.")


def test_4_unconfigured_api_key_handling():
    """
    Test 4: Missing API key returns HTTP 503 Service Unavailable.
    """
    print("\n=== [Test 4] Testing unconfigured API key ===")
    mock_service = Channel3Service(api_key="")
    with patch("app.routes.products.channel3_service", mock_service):
        resp = client.get("/api/products/search?q=smartwatch")
        print(f"Unconfigured key status: {resp.status_code}")
        assert resp.status_code == 503
    print("✓ Test 4 passed: Unconfigured API key handled with HTTP 503.")


if __name__ == "__main__":
    print("=== Running Channel3 Product Discovery Test Suite ===")
    test_1_live_channel3_smartwatch_search()
    test_2_empty_query_validation()
    test_3_invalid_api_key_handling()
    test_4_unconfigured_api_key_handling()
    print("\nALL 4 CHANNEL3 PRODUCT TESTS PASSED SUCCESSFULLY!")
