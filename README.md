# Market Maker Bot

Local-only market-making bot for perpetual futures with uptime optimization and a real-time web dashboard.

> **This system runs entirely on your local machine. No cloud deployment, no public URLs.**

## Architecture

```
┌────────────────────────────────────────────────┐
│         Frontend (React + Vite + Tailwind)      │
│         http://localhost:5173                    │
│         WebSocket → ws://localhost:8000/ws       │
└──────────────────────┬─────────────────────────┘
                       │
┌──────────────────────┴─────────────────────────┐
│              Backend (FastAPI)                   │
│              http://localhost:8000                │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ │
│  │  Auth  │ │ Market │ │Trading │ │  Uptime  │ │
│  │(JWT/WS)│ │  Data  │ │ Engine │ │ Tracker  │ │
│  └────────┘ └────────┘ └────────┘ └──────────┘ │
└──────────────────────┬─────────────────────────┘
                       │
                  ┌────┴────┐
                  │  Perps  │
                  │   API   │
                  └─────────┘
```

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

# Edit .env with your credentials
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
npx vite --port 5173
```

Open your browser:
- **Dashboard:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs

## Environment Variables

All configuration is in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE` | `https://api.example.io` | REST API base URL |
| `WS_URL` | `wss://ws.example.io` | WebSocket URL |
| `PRIVATE_KEY` | — | Wallet private key (hex, no 0x prefix) |
| `SYMBOL` | `ETH-PERP` | Trading pair |
| `SPREAD_BPS` | `5.0` | Half-spread in basis points (each side) |
| `ORDER_SIZE` | `0.1` | Order size in base asset units |
| `REFRESH_INTERVAL` | `5.0` | Seconds between quote refreshes |
| `MAX_NOTIONAL` | `10000.0` | Max notional exposure in USD |
| `MAX_POSITION` | `1.0` | Max absolute position in base asset |
| `MAX_CONSECUTIVE_FAILURES` | `5` | Kill-switch failure threshold |
| `STALE_ORDER_SECONDS` | `30` | Cancel orders older than this |
| `MAX_SPREAD_DEVIATION_BPS` | `10` | Max allowed deviation from mid |
| `UPTIME_TARGET_MINUTES` | `30` | Target active minutes per hour |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/status` | Bot status, mid-price, spread |
| `GET` | `/api/orders` | Active orders list |
| `GET` | `/api/uptime` | Uptime stats (current hour + 24h history) |
| `GET` | `/api/positions` | Position and risk status |
| `POST` | `/api/config` | Update spread_bps, order_size, refresh_interval |
| `POST` | `/api/kill` | Emergency kill switch |
| `WS` | `/ws` | Real-time state broadcast to dashboard |

## Security

> [!CAUTION]
> - Your **private key** is stored in `.env` and loaded into memory only — it is never logged or persisted elsewhere.
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

- **Stability** — graceful error handling, auto-reconnect, exponential backoff
- **Consistent maker uptime** — always maintains both bid and ask within 10 bps
- **Safe order management** — stale orders cancelled automatically
- **Token refresh** — JWT tokens refreshed before expiry
- **Kill switch** — instant order cancellation via dashboard or API

## License

Private — All rights reserved.
