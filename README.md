# StandX Market Maker Bot

Production-ready market-making bot for StandX with uptime optimization and a real-time web dashboard.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                     │
│           Real-time dashboard via WebSocket             │
│        Vite + Tailwind CSS │ Port 3000                  │
└───────────────────────┬─────────────────────────────────┘
                        │ WebSocket + REST
┌───────────────────────┴─────────────────────────────────┐
│                Backend (FastAPI)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │   Auth   │ │  Market  │ │ Trading  │ │  Uptime   │  │
│  │  Module  │ │   Data   │ │  Engine  │ │  Tracker  │  │
│  │ (JWT/WS) │ │ (WS+OB)  │ │ (Quotes) │ │ (30m/hr)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
│                    Port 8000                            │
└───────────────────────┬─────────────────────────────────┘
                        │ REST + WebSocket
                   ┌────┴────┐
                   │ StandX  │
                   │   API   │
                   └─────────┘
```

## Features

- **Uptime Optimization** — Maintains both bid and ask orders within 10 bps of mid-price to maximize maker uptime (30+ min/hour target)
- **Auto-Requoting** — Refreshes quotes every N seconds, cancels stale or drifted orders
- **Risk Management** — Position limits, max notional exposure, reduce-only mode
- **Kill Switch** — Emergency order cancellation via dashboard or API
- **Real-time Dashboard** — Live WebSocket updates showing orders, uptime, PnL, and risk
- **JWT Auth** — Wallet-based signing authentication with auto-refresh

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker & Docker Compose (for containerized deployment)

### Local Development

#### 1. Backend

```bash
cd backend
cp .env.example .env
# Edit .env — set your PRIVATE_KEY and API URLs

python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt

# Run
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at `http://localhost:5173` (proxies API to backend on port 8000).

#### 3. Run Tests

```bash
cd backend
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

### Docker Deployment

```bash
# Create .env
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials

# Build and start
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

Dashboard at `http://localhost:3000`, API at `http://localhost:8000/docs`.

## VPS Deployment

### 1. Server Setup

```bash
# On your VPS (Ubuntu 22.04+)
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable docker

# Clone
git clone https://github.com/cyberatlas-baseeth/makerbot.git
cd makerbot
```

### 2. Configure

```bash
cp backend/.env.example backend/.env
nano backend/.env
# Set: PRIVATE_KEY, STANDX_API_URL, STANDX_WS_URL

# Optionally tune config.yaml
nano backend/config.yaml
```

### 3. Deploy

```bash
docker compose up --build -d
```

### 4. Reverse Proxy (Optional)

If using nginx as a reverse proxy on the host:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
    }

    location /ws {
        proxy_pass http://localhost:3000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Configuration Reference

### config.yaml

| Key | Default | Description |
|-----|---------|-------------|
| `symbol` | `ETH-PERP` | Trading pair |
| `spread_bps` | `5.0` | Half-spread in basis points |
| `order_size` | `0.1` | Order size in base units |
| `refresh_interval` | `5.0` | Seconds between quote refreshes |
| `max_notional` | `10000.0` | Max notional exposure (USD) |
| `max_position` | `1.0` | Max absolute position |
| `uptime_target_minutes` | `30` | Target active minutes per hour |
| `max_consecutive_failures` | `5` | Kill-switch threshold |
| `stale_order_seconds` | `30` | Cancel orders older than this |
| `max_spread_deviation_bps` | `10` | Max allowed deviation from mid |

### Environment Variables (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `PRIVATE_KEY` | Yes | Wallet private key (hex) |
| `STANDX_API_URL` | No | Override API base URL |
| `STANDX_WS_URL` | No | Override WebSocket URL |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/status` | Bot status, mid-price, spread, engine info |
| `GET` | `/api/orders` | Active orders list |
| `GET` | `/api/uptime` | Uptime stats (current + 24h history) |
| `GET` | `/api/positions` | Position & risk status |
| `POST` | `/api/config` | Update spread_bps, order_size, refresh_interval |
| `POST` | `/api/kill` | Emergency kill switch |
| `WS` | `/ws` | Real-time state broadcast |

## Security Considerations

- **Private key** is loaded from `.env` and stored in memory only — never logged or persisted
- **Never commit** `.env` to version control
- **Use HTTPS** in production (terminate TLS at your reverse proxy)
- **Restrict dashboard access** via firewall rules or VPN — the dashboard has control over live trading
- **Kill switch** is always available via `POST /api/kill` even if the dashboard is unreachable
- The bot runs with **post-only orders** to avoid taker fees and unintended market orders

## License

Private — All rights reserved.
