# Market Maker Bot

Uptime-optimized market-making bot with a real-time web dashboard. Places symmetric limit orders around mid price to maintain continuous two-sided quoting.

> **This system runs entirely on your local machine. No cloud deployment, no public URLs.**

## Architecture

```
┌──────────────────────────────────────────────────┐
│         Frontend (React + Vite + TypeScript)      │
│         http://localhost:5173                      │
│         WebSocket → ws://localhost:8000/ws         │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────┴───────────────────────────┐
│              Backend (FastAPI + Python)            │
│              http://localhost:8000                  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌───────────┐  │
│  │  Auth  │ │ Market │ │Trading │ │  Uptime   │  │
│  │JWT/Ed25│ │  Data  │ │ Engine │ │  Tracker  │  │
│  └────────┘ └────────┘ └────────┘ └───────────┘  │
└──────────────────────┬───────────────────────────┘
                       │
                  ┌────┴────┐
                  │ StandX  │
                  │Perps API│
                  └─────────┘
```

## Supported Symbols

| Symbol | Qty Tick | Price Tick | Min Order (approx) |
|--------|----------|------------|---------------------|
| BTC-USD | 0.0001 | 0.01 | ~$6.60 |
| ETH-USD | 0.001 | 0.1 | ~$3.50 |
| XAU-USD | 0.01 | 0.1 | ~$50.00 |
| XAG-USD | 0.1 | 0.01 | ~$3.00 |

> If `bid_notional` / `ask_notional` is below the minimum, the bot automatically uses 1 qty tick.

## How It Works

1. **Connects** to StandX orderbook via WebSocket
2. **Generates quotes** — symmetric bid/ask around mid price at configured `spread_bps`
3. **Places limit orders** — one buy, one sell
4. **Monitors drift** — if mid price moves beyond `requote_threshold_bps`, cancels all orders and places fresh ones
5. **Tracks uptime** — counts seconds where both bid + ask are active on the book
6. **Dashboard** — real-time status via WebSocket (1 Hz updates)

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**

## Setup

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env from template
copy .env.example .env
# (Linux: cp .env.example .env)

# Edit .env with your StandX credentials
# notepad .env
```

### 2. Frontend

```bash
cd frontend
npm install
```

## Running

Open **two terminals**:

**Terminal 1 — Backend:**
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npx vite --host
```

Open your browser:
- **Dashboard:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs

## Environment Variables

All configuration is in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `STANDX_API_BASE` | `https://perps.standx.com` | REST API base URL |
| `STANDX_WS_URL` | `wss://perps.standx.com/ws-stream/v1` | Orderbook WebSocket URL |
| `STANDX_JWT_TOKEN` | — | JWT token from StandX |
| `STANDX_ED25519_PRIVATE_KEY` | — | Ed25519 signing key (base58) |
| `STANDX_WALLET_ADDRESS` | — | Wallet address (0x...) |
| `STANDX_CHAIN` | `bsc` | Chain identifier |
| `SYMBOL` | `BTC-USD` | Trading pair |
| `SPREAD_BPS` | `50.0` | Half-spread each side in basis points |
| `BID_NOTIONAL` | `30.0` | Bid order size in USD |
| `ASK_NOTIONAL` | `30.0` | Ask order size in USD |
| `REFRESH_INTERVAL` | `1.0` | Engine tick interval (seconds) |
| `REQUOTE_THRESHOLD_BPS` | `25.0` | Requote when mid drifts ±X bps |
| `PROXIMITY_GUARD_BPS` | `1.0` | Refresh when order is within X bps of best bid/ask |
| `MAX_NOTIONAL` | `10000.0` | Max notional exposure |
| `MAX_CONSECUTIVE_FAILURES` | `5` | Kill-switch failure threshold |
| `STALE_ORDER_SECONDS` | `30` | Cancel orders older than this |
| `MAX_SPREAD_DEVIATION_BPS` | `200` | Max allowed spread deviation per side |
| `UPTIME_TARGET_MINUTES` | `30` | Target active minutes per hour |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/start` | Start the trading engine |
| `POST` | `/api/stop` | Stop engine and cancel all exchange orders |
| `GET` | `/api/status` | Bot status, mid-price, spread, orders, uptime |
| `GET` | `/api/orders` | Active orders list |
| `GET` | `/api/uptime` | Uptime stats (current hour + 24h history) |
| `POST` | `/api/config` | Update symbol, spread_bps, notionals, requote_threshold_bps |
| `POST` | `/api/kill` | Emergency kill switch |
| `WS` | `/ws` | Real-time state broadcast (1 Hz) |

### Runtime Config (via Dashboard or API)

These can be changed while the bot is running:

- **Symbol** — switches orderbook subscription, cancels orders, restarts engine
- **Spread (bps)** — half-spread each side
- **Bid / Ask Notional ($)** — order size in USD
- **Requote Threshold (bps)** — drift before refreshing orders

## Order Lifecycle

```
Mid price → Generate quote → Place bid + ask
                                    │
                              ┌─────┴──────┐
                              │  Every 1s  │
                              │  check:    │
                              │  - drift   │
                              │  - stale   │
                              │  - prox    │
                              └─────┬──────┘
                                    │
                        Need refresh? ──No──→ Keep orders
                              │
                             Yes
                              │
                    Cancel all on exchange
                    (query_open_orders → cancel_order)
                              │
                    Place fresh bid + ask
```

## Security

> [!CAUTION]
> - Your **JWT token** and **Ed25519 key** are stored in `.env` and loaded into memory only.
> - **Never commit** the `.env` file to version control.
> - This bot is designed for **local use only** — do not expose ports 8000 or 5173 to the internet.
> - The dashboard has **no authentication** — anyone with access to your machine can control the bot.

## Windows Sleep Warning

> [!WARNING]
> If your computer enters **sleep mode**, the bot will pause and miss uptime. To prevent this:
> - Go to **Settings → System → Power & Sleep**
> - Set **Sleep** to **Never** while the bot is running
> - Alternatively, use `powercfg -change -standby-timeout-ac 0` in an admin terminal

## Design Philosophy

This bot is **not** a profit-seeking aggressive trader. It is optimized for:

- **Maker uptime** — always maintains both bid and ask on the book
- **Stability** — graceful error handling, kill switch, auto-reconnect
- **Safe order management** — stale orders cancelled, drift-based requoting
- **Symbol-aware ticks** — correct qty and price tick sizes per symbol
- **Minimal footprint** — no position tracking, no PnL, just place and cancel

## License

Private — All rights reserved.
