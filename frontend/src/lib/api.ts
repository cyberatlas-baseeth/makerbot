// Hardcoded localhost — this bot runs locally only
const API_BASE = 'http://localhost:8000/api';

export async function startBot() {
    const res = await fetch(`${API_BASE}/start`, { method: 'POST' });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Failed to start');
    }
    return res.json();
}

export async function stopBot() {
    const res = await fetch(`${API_BASE}/stop`, { method: 'POST' });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Failed to stop');
    }
    return res.json();
}

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

export async function updateConfig(config: {
    symbol?: string;
    spread_bps?: number;
    bid_notional?: number;
    ask_notional?: number;
    requote_threshold_bps?: number;
    refresh_interval?: number;
    tp_bps?: number;
    sl_bps?: number;
}) {
    const res = await fetch(`${API_BASE}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Failed to update config');
    }
    return res.json();
}
