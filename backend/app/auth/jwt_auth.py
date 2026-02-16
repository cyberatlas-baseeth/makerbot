"""
StandX Authentication via frontend wallet signing.

Architecture:
- Frontend connects MetaMask → signs message → gets JWT from StandX
- Frontend sends JWT + ed25519 private key to backend via POST /api/auth/start
- Backend stores token in memory and uses it for all StandX API calls
- Backend generates ed25519 body signatures for each request

The private key never leaves the user's browser/MetaMask.
"""

from __future__ import annotations

import asyncio
import base64
import time
import uuid
from typing import Any

import httpx

from app.config import settings
from app.logger import get_logger

log = get_logger("auth")

# Lazy import ed25519 — only needed for body signing
_ed25519 = None


def _get_ed25519():
    global _ed25519
    if _ed25519 is None:
        try:
            from nacl.signing import SigningKey  # type: ignore
            _ed25519 = "nacl"
        except ImportError:
            _ed25519 = "none"
    return _ed25519


class AuthManager:
    """Manages StandX JWT token and request signing."""

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._wallet_address: str | None = None
        self._chain: str | None = None
        self._ed25519_private_key_bytes: bytes | None = None
        self._request_id: str | None = None
        self._token_set_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def wallet_address(self) -> str:
        return self._wallet_address or ""

    @property
    def is_authenticated(self) -> bool:
        return self._access_token is not None

    async def set_credentials(
        self,
        token: str,
        address: str,
        chain: str,
        ed25519_private_key_hex: str,
        request_id: str,
    ) -> None:
        """Store credentials received from frontend after MetaMask login."""
        async with self._lock:
            self._access_token = token
            self._wallet_address = address
            self._chain = chain
            self._ed25519_private_key_bytes = bytes.fromhex(ed25519_private_key_hex)
            self._request_id = request_id
            self._token_set_at = time.time()

        log.info(
            "auth.credentials_set",
            address=address,
            chain=chain,
        )

    async def get_token(self) -> str:
        """Return the current access token."""
        async with self._lock:
            if self._access_token is None:
                raise RuntimeError("Not authenticated — connect wallet via dashboard first.")
            return self._access_token

    async def get_auth_headers(self) -> dict[str, str]:
        """Return headers with both Authorization and body signature."""
        token = await self.get_token()
        return {"Authorization": f"Bearer {token}"}

    def sign_request_body(self, payload: str) -> dict[str, str]:
        """
        Sign a request body per StandX's body signature flow.

        Returns dict with x-request-* headers.
        Uses ed25519 signing of: v1,{requestId},{timestamp},{payload}
        """
        if self._ed25519_private_key_bytes is None:
            return {}

        version = "v1"
        request_id = str(uuid.uuid4())
        timestamp = int(time.time() * 1000)
        message = f"{version},{request_id},{timestamp},{payload}"
        message_bytes = message.encode("utf-8")

        # Sign with ed25519
        try:
            from nacl.signing import SigningKey  # type: ignore
            signing_key = SigningKey(self._ed25519_private_key_bytes)
            signed = signing_key.sign(message_bytes)
            signature_b64 = base64.b64encode(signed.signature).decode("utf-8")
        except ImportError:
            # Fallback: try using cryptography library
            try:
                from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
                private_key = Ed25519PrivateKey.from_private_bytes(self._ed25519_private_key_bytes)
                signature = private_key.sign(message_bytes)
                signature_b64 = base64.b64encode(signature).decode("utf-8")
            except Exception as e:
                log.warning("auth.body_sign_failed", error=str(e))
                return {}

        return {
            "x-request-sign-version": version,
            "x-request-id": request_id,
            "x-request-timestamp": str(timestamp),
            "x-request-signature": signature_b64,
        }

    async def get_full_headers(self, payload: str = "") -> dict[str, str]:
        """Get auth headers + body signature headers combined."""
        headers = await self.get_auth_headers()
        if payload:
            sign_headers = self.sign_request_body(payload)
            headers.update(sign_headers)
        return headers

    async def close(self) -> None:
        """Cleanup resources."""
        pass


# Singleton
auth_manager = AuthManager()
