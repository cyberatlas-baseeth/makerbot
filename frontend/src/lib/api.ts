// Hardcoded localhost — this bot runs locally only
const API_BASE = 'http://localhost:8000/api';

export async function fetchStatus() {
    const res = await fetch(`${API_BASE}/status`);
    return res.json();
}

export async function fetchOrders() {
    const res = await fetch(`${API_BASE}/orders`);
    return res.json();
}

export async function fetchUptime() {
    const res = await fetch(`${API_BASE}/uptime`);
    return res.json();
}

export async function fetchPositions() {
    const res = await fetch(`${API_BASE}/positions`);
    return res.json();
}

export async function updateConfig(config: {
    spread_bps?: number;
    order_size?: number;
    refresh_interval?: number;
}) {
    const res = await fetch(`${API_BASE}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
    });
    return res.json();
}

export async function killBot() {
    const res = await fetch(`${API_BASE}/kill`, {
        method: 'POST',
    });
    return res.json();
}
