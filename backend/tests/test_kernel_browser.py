"""
KERNEL Cloud Browser Integration Test Suite.
Validates end-to-end cloud browser lifecycle:
1. Session creation (POST /api/browser/start)
2. Live page DOM inspection (POST /api/browser/inspect)
3. Session termination (POST /api/browser/close)
4. Confirm closure (404 on subsequent inspection/close)
5. Invalid session ID handling (404)
6. Unconfigured API key handling (503)
7. Security check (Zero API key leakage in responses)
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
from app.services.kernel_service import KernelService

client = TestClient(app)


def test_kernel_browser_full_lifecycle():
    """
    Executes the real KERNEL cloud browser end-to-end integration:
    - Spawns browser navigating to https://example.com
    - Inspects page title and URL
    - Closes browser session
    - Verifies closure
    """
    print("\n=== [1/5] Testing POST /api/browser/start ===")
    start_payload = {
        "merchant_url": "https://example.com",
        "timeout_seconds": 120
    }
    start_resp = client.post("/api/browser/start", json=start_payload)
    print(f"Start HTTP Status: {start_resp.status_code}")
    assert start_resp.status_code == 200, f"Expected 200, got {start_resp.status_code}: {start_resp.text}"

    start_data = start_resp.json()
    print(f"Start Response: {start_data}")
    session_id = start_data.get("session_id")
    live_view_url = start_data.get("live_view_url")

    assert session_id, "session_id was not returned"
    assert start_data.get("merchant_url") == "https://example.com"
    assert start_data.get("status") == "active"
    assert live_view_url and "kernel.sh" in live_view_url, f"Expected live view URL from kernel.sh, got: {live_view_url}"

    # SECURITY CHECK
    raw_text = start_resp.text.lower()
    assert "kernel_api_key" not in raw_text, "SECURITY VIOLATION: KERNEL_API_KEY exposed!"
    print(f"✓ Browser session created: {session_id}")
    print(f"✓ Live View URL retrieved: {live_view_url}")

    try:
        print("\n=== [2/5] Testing POST /api/browser/inspect ===")
        inspect_resp = client.post("/api/browser/inspect", json={"session_id": session_id})
        print(f"Inspect HTTP Status: {inspect_resp.status_code}")
        assert inspect_resp.status_code == 200, f"Expected 200, got {inspect_resp.status_code}: {inspect_resp.text}"

        inspect_data = inspect_resp.json()
        print(f"Inspect Response: {inspect_data}")
        assert inspect_data.get("session_id") == session_id
        assert inspect_data.get("title") == "Example Domain", f"Unexpected title: {inspect_data.get('title')}"
        assert "example.com" in inspect_data.get("url", "")
        assert inspect_data.get("success") is True
        assert inspect_data.get("content_preview") is not None
        print(f"✓ Inspected title: '{inspect_data.get('title')}'")
        print(f"✓ Current URL: '{inspect_data.get('url')}'")
        print(f"✓ Content preview: {inspect_data.get('content_preview')[:80]}...")

    finally:
        print("\n=== [3/5] Testing POST /api/browser/close ===")
        close_resp = client.post("/api/browser/close", json={"session_id": session_id})
        print(f"Close HTTP Status: {close_resp.status_code}")
        assert close_resp.status_code == 200, f"Expected 200, got {close_resp.status_code}: {close_resp.text}"

        close_data = close_resp.json()
        print(f"Close Response: {close_data}")
        assert close_data.get("session_id") == session_id
        assert close_data.get("status") == "closed"
        print(f"✓ Browser session closed: {session_id}")

    print("\n=== [4/5] Confirming Session Closure ===")
    # Re-inspecting closed session must return 404 Not Found
    re_inspect = client.post("/api/browser/inspect", json={"session_id": session_id})
    print(f"Re-inspect HTTP Status (expected 404): {re_inspect.status_code}")
    assert re_inspect.status_code == 404, f"Expected 404, got {re_inspect.status_code}"

    # Re-closing closed session must return 404 Not Found
    re_close = client.post("/api/browser/close", json={"session_id": session_id})
    print(f"Re-close HTTP Status (expected 404): {re_close.status_code}")
    assert re_close.status_code == 404, f"Expected 404, got {re_close.status_code}"
    print("✓ Confirmed session was fully deleted from KERNEL.")


def test_invalid_session_id():
    """
    Test invalid / non-existent session ID handling.
    """
    print("\n=== [5a] Testing Non-existent Session ID ===")
    resp = client.post("/api/browser/inspect", json={"session_id": "non_existent_session_999"})
    print(f"Invalid Session ID Status (expected 404): {resp.status_code}")
    assert resp.status_code == 404


def test_unconfigured_api_key():
    """
    Test missing KERNEL_API_KEY handling (HTTP 503).
    """
    print("\n=== [5b] Testing Unconfigured API Key ===")
    mock_service = KernelService(api_key="")
    with patch("app.routes.browser.kernel_service", mock_service):
        resp = client.post("/api/browser/start", json={"merchant_url": "https://example.com"})
        print(f"Unconfigured Key Status (expected 503): {resp.status_code}")
        assert resp.status_code == 503
        assert "KERNEL_API_KEY" in resp.json().get("detail", "")


if __name__ == "__main__":
    print("=== Running KERNEL Cloud Browser Test Suite ===")
    test_kernel_browser_full_lifecycle()
    test_invalid_session_id()
    test_unconfigured_api_key()
    print("\nALL KERNEL CLOUD BROWSER TESTS PASSED SUCCESSFULLY!")
