"""
StandX JWT Authentication via wallet signing.

Flow:
1. Request a challenge/nonce from StandX API.
2. Sign the challenge with the wallet private key (eth_account).
3. Submit signature to receive a JWT access token + refresh token.
4. Auto-refresh before expiry.
5. Token stored in-memory only — never persisted to disk.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct

from app.config import settings
from app.logger import get_logger

log = get_logger("auth")


class AuthManager:
    """Manages StandX JWT authentication lifecycle."""

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry: float = 0.0
        self._refresh_expiry: float = 0.0
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            base_url=settings.standx_api_base,
            timeout=10.0,
        )
        self._account = Account.from_key(settings.private_key) if settings.private_key else None
        self._refresh_task: asyncio.Task[None] | None = None

    @property
    def wallet_address(self) -> str:
        """Return the wallet address derived from the private key."""
        if self._account is None:
            return ""
        return self._account.address

    async def login(self) -> str:
        """
        Full login flow:
        1. GET /auth/challenge?address=<wallet>
        2. Sign the challenge message
        3. POST /auth/login with address + signature
        4. Store tokens in memory
        """
        if self._account is None:
            raise RuntimeError("No private key configured — cannot authenticate.")

        address = self._account.address
        log.info("auth.login.start", address=address)

        # Step 1: Get challenge
        resp = await self._client.get(
            "/auth/challenge",
            params={"address": address},
        )
        resp.raise_for_status()
        challenge_data = resp.json()
        challenge_message: str = challenge_data.get("message", challenge_data.get("challenge", ""))

        # Step 2: Sign challenge
        message = encode_defunct(text=challenge_message)
        signed = self._account.sign_message(message)
        signature = signed.signature.hex()
        if not signature.startswith("0x"):
            signature = "0x" + signature

        # Step 3: Submit signature
        resp = await self._client.post(
            "/auth/login",
            json={
                "address": address,
                "signature": signature,
            },
        )
        resp.raise_for_status()
        token_data = resp.json()

        async with self._lock:
            self._access_token = token_data["access_token"]
            self._refresh_token = token_data.get("refresh_token")
            # Default: access token valid for 15 min, refresh for 24h
            self._token_expiry = time.time() + token_data.get("expires_in", 900)
            self._refresh_expiry = time.time() + token_data.get("refresh_expires_in", 86400)

        log.info("auth.login.success", address=address)

        # Start auto-refresh background task
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._auto_refresh_loop())

        return self._access_token  # type: ignore[return-value]

    async def refresh(self) -> str:
        """Refresh the access token using the refresh token."""
        async with self._lock:
            if not self._refresh_token:
                raise RuntimeError("No refresh token available — must login first.")
            refresh_tok = self._refresh_token

        log.info("auth.refresh.start")
        resp = await self._client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_tok},
        )
        resp.raise_for_status()
        token_data = resp.json()

        async with self._lock:
            self._access_token = token_data["access_token"]
            if "refresh_token" in token_data:
                self._refresh_token = token_data["refresh_token"]
            self._token_expiry = time.time() + token_data.get("expires_in", 900)

        log.info("auth.refresh.success")
        return self._access_token  # type: ignore[return-value]

    async def get_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        async with self._lock:
            token = self._access_token
            expiry = self._token_expiry

        if token is None:
            return await self.login()

        # Refresh 60 seconds before expiry
        if time.time() > expiry - 60:
            try:
                return await self.refresh()
            except Exception:
                log.warning("auth.refresh.failed, re-logging in")
                return await self.login()

        return token

    async def get_auth_headers(self) -> dict[str, str]:
        """Return headers dict with Authorization bearer token."""
        token = await self.get_token()
        return {"Authorization": f"Bearer {token}"}

    async def _auto_refresh_loop(self) -> None:
        """Background loop that refreshes the token before expiry."""
        while True:
            try:
                async with self._lock:
                    expiry = self._token_expiry
                # Sleep until 90 seconds before expiry
                sleep_for = max(expiry - time.time() - 90, 10)
                await asyncio.sleep(sleep_for)
                await self.refresh()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("auth.auto_refresh.error", error=str(e))
                await asyncio.sleep(30)

    async def close(self) -> None:
        """Cleanup resources."""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
        await self._client.aclose()


# Singleton
auth_manager = AuthManager()
