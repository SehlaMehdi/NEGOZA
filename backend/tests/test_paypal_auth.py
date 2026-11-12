"""
PayPal Sandbox Authentication Test Suite
Tests live PayPal Sandbox OAuth 2.0 authentication and verifies security protections:
- Never exposes access tokens or client secrets in responses or logs.
- Properly handles valid credentials, invalid credentials, unconfigured states, and network timeouts.
"""

import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock
import httpx

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env", override=True)

from fastapi.testclient import TestClient
from app.main import app
from app.services.paypal_service import PayPalService

client = TestClient(app)


def test_1_live_paypal_sandbox_authentication():
    """
    Test 1: Live PayPal Sandbox OAuth 2.0 Authentication.
    Calls GET /api/payments/paypal/status with live sandbox credentials from backend/.env.
    """
    print("\n[Test 1] Testing live PayPal Sandbox authentication...")
    response = client.get("/api/payments/paypal/status")

    print(f"HTTP Status: {response.status_code}")
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"

    data = response.json()
    print(f"Response data: {data}")

    # Core assertions
    assert data["status"] == "authenticated", f"Expected status 'authenticated', got {data.get('status')}"
    assert data["authenticated"] is True, "Expected authenticated=True"
    assert data["environment"] == "sandbox", f"Expected sandbox environment, got {data.get('environment')}"
    assert "paypal.com" in data["base_url"]
    assert data.get("app_id") is not None, "Expected valid PayPal App ID"
    assert data.get("token_type") == "Bearer"
    assert isinstance(data.get("expires_in"), int)
    assert data.get("expires_in") > 0

    # SECURITY CHECK: Ensure sensitive tokens/secrets are NEVER exposed in response
    assert "access_token" not in data, "SECURITY VIOLATION: access_token must not be exposed!"
    assert "client_secret" not in data, "SECURITY VIOLATION: client_secret must not be exposed!"
    assert "secret" not in data, "SECURITY VIOLATION: secret must not be exposed!"

    print("✓ Test 1 passed: Live PayPal Sandbox authentication verified successfully.")


def test_2_invalid_credentials_handling():
    """
    Test 2: Invalid Credentials Handling.
    Verifies that invalid Client Secret returns HTTP 401 Unauthorized without crashing.
    """
    print("\n[Test 2] Testing invalid credentials handling...")
    mock_service = PayPalService(
        client_id="invalid_client_id_12345",
        client_secret="invalid_secret_67890",
        base_url="https://api-m.sandbox.paypal.com"
    )

    with patch("app.routes.payments.paypal_service", mock_service):
        response = client.get("/api/payments/paypal/status")
        print(f"Invalid credentials HTTP Status: {response.status_code}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        assert "failed" in response.text.lower() or "authentication" in response.text.lower()

    print("✓ Test 2 passed: Invalid credentials handled with HTTP 401.")


def test_3_unconfigured_credentials_handling():
    """
    Test 3: Missing / Unconfigured Credentials Handling.
    Verifies that missing credentials return HTTP 503 Service Unavailable.
    """
    print("\n[Test 3] Testing unconfigured credentials handling...")
    mock_service = PayPalService(
        client_id="",
        client_secret="",
        base_url="https://api-m.sandbox.paypal.com"
    )

    with patch("app.routes.payments.paypal_service", mock_service):
        response = client.get("/api/payments/paypal/status")
        print(f"Unconfigured credentials HTTP Status: {response.status_code}")
        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        assert "credentials are missing" in response.text.lower() or "unconfigured" in response.text.lower()

    print("✓ Test 3 passed: Unconfigured credentials handled with HTTP 503.")


def test_4_network_timeout_handling():
    """
    Test 4: Network Timeout Handling.
    Verifies that network timeouts return HTTP 504 Gateway Timeout.
    """
    print("\n[Test 4] Testing network timeout handling...")
    with patch.object(
        PayPalService,
        "verify_sandbox_authentication",
        AsyncMock(side_effect=TimeoutError("PayPal Sandbox API request timed out."))
    ):
        response = client.get("/api/payments/paypal/status")
        print(f"Timeout HTTP Status: {response.status_code}")
        assert response.status_code == 504, f"Expected 504, got {response.status_code}"

    print("✓ Test 4 passed: Network timeout handled with HTTP 504.")


def test_5_connection_error_handling():
    """
    Test 5: Connection Failure Handling.
    Verifies that connection errors return HTTP 502 Bad Gateway.
    """
    print("\n[Test 5] Testing connection error handling...")
    with patch.object(
        PayPalService,
        "verify_sandbox_authentication",
        AsyncMock(side_effect=ConnectionError("Unable to reach PayPal Sandbox server."))
    ):
        response = client.get("/api/payments/paypal/status")
        print(f"Connection error HTTP Status: {response.status_code}")
        assert response.status_code == 502, f"Expected 502, got {response.status_code}"

    print("✓ Test 5 passed: Connection failure handled with HTTP 502.")


if __name__ == "__main__":
    print("=== Running PayPal Sandbox Authentication Test Suite ===")
    test_1_live_paypal_sandbox_authentication()
    test_2_invalid_credentials_handling()
    test_3_unconfigured_credentials_handling()
    test_4_network_timeout_handling()
    test_5_connection_error_handling()
    print("\nALL 5 PAYPAL SANDBOX AUTHENTICATION TESTS PASSED SUCCESSFULLY!")
