"""
StandX Authentication — credentials loaded from .env.

The JWT token and ed25519 private key are set in .env.
The bot authenticates automatically on startup — no MetaMask needed.
Body signatures use ed25519 for order/cancel requests.
"""

from __future__ import annotations

import base64
import time
import uuid
from typing import Any

from app.config import settings
from app.logger import get_logger

log = get_logger("auth")


def _decode_ed25519_key(key_str: str) -> bytes | None:
    """Decode ed25519 private key from base58 string."""
    if not key_str:
        return None
    try:
        from base58 import b58decode  # type: ignore
        return b58decode(key_str)
    except ImportError:
        # Fallback: try raw bytes interpretation
        try:
            return bytes.fromhex(key_str)
        except ValueError:
            log.warning("auth.key_decode_failed", hint="Install base58: pip install base58")
            return None


class AuthManager:
    """Manages StandX JWT token and request signing from .env credentials."""

    def __init__(self) -> None:
        self._access_token: str = settings.standx_jwt_token
        self._wallet_address: str = settings.standx_wallet_address
        self._chain: str = settings.standx_chain
        self._ed25519_private_key_bytes: bytes | None = _decode_ed25519_key(
            settings.standx_ed25519_private_key
        )
        self._token_set_at: float = time.time()

        if self._access_token:
            log.info(
                "auth.loaded_from_env",
                address=self._wallet_address,
                chain=self._chain,
                has_ed25519=self._ed25519_private_key_bytes is not None,
            )
        else:
            log.warning("auth.no_token", hint="Set STANDX_JWT_TOKEN in .env")

    @property
    def wallet_address(self) -> str:
        return self._wallet_address or ""

    @property
    def is_authenticated(self) -> bool:
        return bool(self._access_token)

    async def get_token(self) -> str:
        """Return the current access token."""
        if not self._access_token:
            raise RuntimeError("Not authenticated — set STANDX_JWT_TOKEN in .env")
        return self._access_token

    async def get_auth_headers(self) -> dict[str, str]:
        """Return Authorization header."""
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
