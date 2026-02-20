"""
FastAPI application entry point.

Initializes all modules. Credentials loaded from .env (no MetaMask).
Trading engine starts via POST /api/start from the dashboard.
Runs locally on localhost:8000.
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
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
market_data_client = MarketDataClient(orderbook=orderbook)
trading_engine = TradingEngine(orderbook=orderbook)

# Wire up API references
routes.set_engine(trading_engine)
routes.set_orderbook(orderbook)
routes.set_market_data_client(market_data_client)
ws.set_engine(trading_engine)
ws.set_orderbook(orderbook)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    log.info(
        "app.starting",
        symbol=settings.symbol,
        authenticated=auth_manager.is_authenticated,
        wallet=auth_manager.wallet_address,
    )

    broadcast_task: asyncio.Task[None] | None = None
    try:
        # Start market data WebSocket feed
        await market_data_client.start()

        # Wait briefly for initial orderbook data
        await asyncio.sleep(2.0)

        # Engine starts via POST /api/start from dashboard
        log.info(
            "app.ready",
            message="Click Start in the dashboard to begin trading",
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
    title="Market Maker Bot",
    description="Local market-making bot with uptime optimization",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend on localhost:5173 (dev) and same-origin (exe)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(routes.router, prefix="/api")
app.include_router(ws.router)


# ── Static file serving (frontend build) ─────────────────────────
def _get_static_dir() -> Path | None:
    """Find the frontend dist directory."""
    if getattr(sys, "frozen", False):
        # PyInstaller: files extracted to _MEIPASS
        bundle_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        dist = bundle_dir / "frontend_dist"
        if dist.exists():
            return dist
    else:
        # Development: look for frontend/dist relative to backend
        dev_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
        if dev_dist.exists():
            return dev_dist
    return None


_static_dir = _get_static_dir()

if _static_dir:
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    @app.get("/")
    async def root():
        return FileResponse(_static_dir / "index.html")

    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(_static_dir / "assets")), name="static")

    # SPA fallback — any unknown route serves index.html
    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        # Try exact file first
        file = _static_dir / path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_static_dir / "index.html")
else:
    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": "Market Maker Bot",
            "version": "2.0.0",
            "docs": "/docs",
            "note": "Frontend not found. Run 'npm run build' in frontend/ first.",
        }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
