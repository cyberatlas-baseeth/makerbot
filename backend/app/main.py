"""
FastAPI application entry point.

Initializes all modules and starts the trading engine on startup.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logger import setup_logging, get_logger
from app.auth.jwt_auth import auth_manager
from app.market_data.orderbook import Orderbook
from app.market_data.ws_client import MarketDataClient
from app.trading.engine import TradingEngine
from app.api import routes, ws

# Setup logging first
setup_logging()
log = get_logger("main")

# Core instances
orderbook = Orderbook(symbol=settings.symbol)
market_data_client = MarketDataClient(
    orderbook=orderbook,
    auth_headers_fn=auth_manager.get_auth_headers,
)
trading_engine = TradingEngine(orderbook=orderbook)

# Wire up API references
routes.set_engine(trading_engine)
routes.set_orderbook(orderbook)
ws.set_engine(trading_engine)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    log.info("app.starting", symbol=settings.symbol)

    # Startup sequence
    broadcast_task: asyncio.Task[None] | None = None
    try:
        # 1. Authenticate
        if settings.private_key and settings.private_key != "your_private_key_here":
            try:
                await auth_manager.login()
                log.info("app.authenticated")
            except Exception as e:
                log.error("app.auth_failed", error=str(e))
                log.warning("app.running_without_auth")
        else:
            log.warning("app.no_private_key — running in monitor-only mode")

        # 2. Start market data feed
        await market_data_client.start()

        # 3. Wait briefly for initial orderbook data
        await asyncio.sleep(2.0)

        # 4. Start trading engine
        if settings.private_key and settings.private_key != "your_private_key_here":
            await trading_engine.start()
        else:
            log.warning("app.engine_not_started — no private key")

        # 5. Start WebSocket broadcast
        broadcast_task = asyncio.create_task(ws.broadcast_loop())

        log.info("app.started")
        yield

    finally:
        # Shutdown sequence
        log.info("app.shutting_down")

        if broadcast_task and not broadcast_task.done():
            broadcast_task.cancel()

        await trading_engine.stop()
        await market_data_client.stop()
        await auth_manager.close()
        await trading_engine.close()

        log.info("app.shutdown_complete")


# Create FastAPI app
app = FastAPI(
    title="StandX Market Maker Bot",
    description="Production market-making bot for StandX with uptime optimization",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(routes.router, prefix="/api")
app.include_router(ws.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "StandX Market Maker Bot",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
