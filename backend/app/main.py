"""
FastAPI application entry point.

Initializes all modules. Trading engine starts AFTER frontend sends
the JWT token via POST /api/auth/start (MetaMask sign-in flow).
Runs locally on localhost:8000.
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

    broadcast_task: asyncio.Task[None] | None = None
    try:
        # Start market data WebSocket feed (public, no auth needed)
        await market_data_client.start()

        # Wait briefly for initial orderbook data
        await asyncio.sleep(2.0)

        # Engine will be started by POST /api/auth/start after MetaMask login
        log.info(
            "app.waiting_for_auth",
            message="Connect wallet via dashboard to start trading engine",
        )

        # Start WebSocket broadcast to frontend
        broadcast_task = asyncio.create_task(ws.broadcast_loop())

        log.info("app.started", api="http://localhost:8000", docs="http://localhost:8000/docs")
        yield

    finally:
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
    description="Local market-making bot for StandX with uptime optimization",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend on localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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
