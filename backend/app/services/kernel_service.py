"""
KERNEL Cloud Browser Service.
Integrates with the official KERNEL Python SDK (AsyncKernel) to provide sandboxed,
observable cloud browser sessions for merchant page inspection and live viewing.

SECURITY:
- Never exposes or logs the KERNEL_API_KEY.
- Operates in inspection/read-only mode.
- Does not perform login, checkout, or bypass CAPTCHAs.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from kernel import (
    AsyncKernel,
    NotFoundError,
    APIStatusError,
    AuthenticationError,
    PermissionDeniedError,
    APITimeoutError,
    APIConnectionError,
    KernelError,
)

logger = logging.getLogger(__name__)

# Ensure backend/.env is loaded
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)


class KernelService:
    """
    Service managing KERNEL cloud browser lifecycles, automated inspection,
    and real-time live view streaming.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self._client: Optional[AsyncKernel] = None
        # In-memory registry tracking created sessions: session_id -> metadata
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    @property
    def api_key(self) -> str:
        key = self._api_key if self._api_key is not None else os.getenv("KERNEL_API_KEY", "")
        return key.strip()

    def is_configured(self) -> bool:
        """Verifies if a valid non-placeholder KERNEL_API_KEY is present."""
        key = self.api_key
        if not key or key in ("", "your_kernel_api_key_here"):
            return False
        return True

    def _get_client(self) -> AsyncKernel:
        """Lazily initializes the AsyncKernel client using the secure API key."""
        if not self.is_configured():
            raise ValueError(
                "KERNEL_API_KEY is missing or unconfigured. "
                "Please configure a valid KERNEL_API_KEY in backend/.env"
            )

        if self._client is None or self._client.api_key != self.api_key:
            self._client = AsyncKernel(api_key=self.api_key)
        return self._client

    async def start_browser(self, merchant_url: str, timeout_seconds: int = 300) -> Dict[str, Any]:
        """
        Creates an isolated KERNEL cloud browser session and navigates to the merchant URL.

        Args:
            merchant_url: Target URL to open in the browser.
            timeout_seconds: Inactivity timeout before automatic reclamation.

        Returns:
            Dict containing session_id, merchant_url, live_view_url, status, and creation metadata.
        """
        clean_url = merchant_url.strip()
        if not clean_url:
            raise ValueError("merchant_url cannot be empty.")

        client = self._get_client()

        logger.info(f"Spawning KERNEL cloud browser for target: {clean_url}")
        try:
            # Create headful browser session so live view URL is generated
            browser = await client.browsers.create(
                start_url=clean_url,
                timeout_seconds=timeout_seconds,
                headless=False,
                stealth=False
            )

            session_id = browser.session_id
            live_view_url = browser.browser_live_view_url
            created_at = browser.created_at.isoformat() if browser.created_at else None

            session_data = {
                "session_id": session_id,
                "merchant_url": clean_url,
                "live_view_url": live_view_url,
                "status": "active",
                "created_at": created_at,
                "message": f"Cloud browser session successfully started at {clean_url}"
            }

            self._active_sessions[session_id] = session_data
            logger.info(f"KERNEL browser session created: {session_id}")
            return session_data

        except (AuthenticationError, PermissionDeniedError) as auth_err:
            logger.error("KERNEL authentication failure: Invalid or unauthorized API key.")
            raise PermissionError("KERNEL API authentication failed: Check KERNEL_API_KEY in backend/.env") from auth_err

        except APITimeoutError as time_err:
            logger.error("KERNEL API request timed out during session creation.")
            raise TimeoutError("KERNEL cloud browser creation timed out.") from time_err

        except APIConnectionError as conn_err:
            logger.error("Failed to connect to KERNEL API service.")
            raise ConnectionError("Unable to reach KERNEL API. Network error or service unreachable.") from conn_err

        except KernelError as k_err:
            logger.error(f"KERNEL API error: {k_err}")
            raise RuntimeError(f"KERNEL service error: {str(k_err)}") from k_err

    async def inspect_browser(self, session_id: str) -> Dict[str, Any]:
        """
        Executes safe Playwright inspection against the active browser session
        to extract the current page title, URL, text content, and live view URL.

        Args:
            session_id: Active KERNEL browser session ID.

        Returns:
            Dict containing session_id, title, url, content_preview, and live_view_url.
        """
        clean_id = (session_id or "").strip()
        if not clean_id:
            raise ValueError("session_id cannot be empty.")

        client = self._get_client()

        # Playwright code executed in the browser VM
        inspect_script = """
        return {
            title: await page.title(),
            url: page.url(),
            content: (await page.textContent('body'))?.trim().slice(0, 1000)
        };
        """

        try:
            # Execute Playwright automation against the active session
            result = await client.browsers.playwright.execute(
                clean_id,
                code=inspect_script,
                timeout_sec=30
            )

            # Retrieve session details to maintain fresh live view URL
            live_view_url = None
            try:
                details = await client.browsers.retrieve(clean_id)
                live_view_url = details.browser_live_view_url
            except Exception:
                # Fallback to locally cached live view URL if available
                if clean_id in self._active_sessions:
                    live_view_url = self._active_sessions[clean_id].get("live_view_url")

            payload = result.result or {}
            title = payload.get("title")
            current_url = payload.get("url")
            content_preview = payload.get("content")

            return {
                "session_id": clean_id,
                "title": title,
                "url": current_url,
                "content_preview": content_preview,
                "live_view_url": live_view_url,
                "success": bool(result.success),
                "message": f"Successfully inspected page '{title or current_url}'."
            }

        except (NotFoundError, APIStatusError) as nf_err:
            if isinstance(nf_err, NotFoundError) or getattr(nf_err, "status_code", None) in (404, 410):
                # Session expired, terminated, or non-existent
                self._active_sessions.pop(clean_id, None)
                logger.warning(f"Browser session not found or already closed: {clean_id}")
                raise KeyError(f"Browser session '{clean_id}' was not found or has expired.") from nf_err
            logger.error(f"KERNEL status error during inspection: {nf_err}")
            raise RuntimeError(f"KERNEL inspection error: {str(nf_err)}") from nf_err

        except (AuthenticationError, PermissionDeniedError) as auth_err:
            logger.error("KERNEL authentication error during inspection.")
            raise PermissionError("KERNEL API authentication failed.") from auth_err

        except APITimeoutError as time_err:
            logger.error(f"Inspection timed out for session: {clean_id}")
            raise TimeoutError("KERNEL page inspection timed out.") from time_err

        except APIConnectionError as conn_err:
            logger.error("Connection error communicating with KERNEL during inspection.")
            raise ConnectionError("Unable to reach KERNEL API service.") from conn_err

        except KernelError as k_err:
            logger.error(f"KERNEL error during inspection: {k_err}")
            raise RuntimeError(f"KERNEL inspection error: {str(k_err)}") from k_err

    async def close_browser(self, session_id: str) -> Dict[str, Any]:
        """
        Terminates the KERNEL cloud browser session and cleans up resources.

        Args:
            session_id: Active KERNEL browser session ID to delete.

        Returns:
            Dict confirming closure status.
        """
        clean_id = (session_id or "").strip()
        if not clean_id:
            raise ValueError("session_id cannot be empty.")

        client = self._get_client()

        try:
            await client.browsers.delete_by_id(clean_id)
            self._active_sessions.pop(clean_id, None)
            logger.info(f"KERNEL browser session terminated: {clean_id}")

            return {
                "session_id": clean_id,
                "status": "closed",
                "message": f"Browser session '{clean_id}' successfully terminated."
            }

        except (NotFoundError, APIStatusError) as nf_err:
            if isinstance(nf_err, NotFoundError) or getattr(nf_err, "status_code", None) in (404, 410):
                # Session was already deleted or expired
                self._active_sessions.pop(clean_id, None)
                logger.warning(f"Browser session already deleted: {clean_id}")
                raise KeyError(f"Browser session '{clean_id}' not found or already closed.") from nf_err
            logger.error(f"KERNEL status error during closure: {nf_err}")
            raise RuntimeError(f"KERNEL closure error: {str(nf_err)}") from nf_err

        except (AuthenticationError, PermissionDeniedError) as auth_err:
            logger.error("KERNEL authentication error during session closure.")
            raise PermissionError("KERNEL API authentication failed.") from auth_err

        except APITimeoutError as time_err:
            logger.error(f"Timeout during session deletion: {clean_id}")
            raise TimeoutError("KERNEL session closure timed out.") from time_err

        except APIConnectionError as conn_err:
            logger.error("Connection error communicating with KERNEL during closure.")
            raise ConnectionError("Unable to reach KERNEL API service.") from conn_err

        except KernelError as k_err:
            logger.error(f"KERNEL error during session closure: {k_err}")
            raise RuntimeError(f"KERNEL closure error: {str(k_err)}") from k_err


# Singleton instance for application reuse
kernel_service = KernelService()
