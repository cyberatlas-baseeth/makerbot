import { useEffect, useRef, useState, useCallback } from 'react';

export interface BotState {
    status: string;
    symbol: string;
    mid_price: number | null;
    best_bid: number | null;
    best_ask: number | null;
    market_spread_bps: number | null;
    configured_spread_bps: number;
    bid_notional: number;
    ask_notional: number;
    requote_threshold_bps: number;
    bid_spread_bps: number;
    ask_spread_bps: number;
    refresh_interval: number;
    tp_bps: number;
    sl_bps: number;
    active_orders: Order[];
    active_order_count: number;
    last_quote: Quote | null;
    loop_count: number;
    consecutive_failures: number;
    uptime: UptimeStats;
    uptime_percentage: number;
    mm_uptime_percentage: number;
}

export interface Order {
    order_id: string;
    side: string;
    price: number;
    size: number;
    placed_at: number;
    status: string;
    age_seconds: number;
}

export interface Quote {
    bid_price: number;
    bid_size: number;
    ask_price: number;
    ask_size: number;
    mid_price: number;
    spread_bps: number;
    bid_spread_bps: number;
    ask_spread_bps: number;
    bid_deviation_bps: number;
    ask_deviation_bps: number;
    within_limits: boolean;
}

export interface UptimeStats {
    current_hour: {
        maker_active_seconds: number;
        mm_active_seconds: number;
        total_elapsed_seconds: number;
        maker_uptime_pct: number;
        mm_uptime_pct: number;
        target_seconds: number;
        maker_target_met: boolean;
        seconds_remaining_for_target: number;
        seconds_elapsed_in_hour: number;
        is_active: boolean;
    };
    history: Array<{
        hour_start: number;
        maker_active_seconds: number;
        mm_active_seconds: number;
        maker_uptime_pct: number;
        mm_uptime_pct: number;
        maker_target_met: boolean;
    }>;
    hours_target_met_last_24h: number;
    avg_maker_uptime_pct_last_24h: number;
    avg_mm_uptime_pct_last_24h: number;
}

const INITIAL_STATE: BotState = {
    status: 'stopped',
    symbol: '-',
    mid_price: null,
    best_bid: null,
    best_ask: null,
    market_spread_bps: null,
    configured_spread_bps: 0,
    bid_notional: 500,
    ask_notional: 500,
    requote_threshold_bps: 25,
    bid_spread_bps: 0,
    ask_spread_bps: 0,
    refresh_interval: 0,
    tp_bps: 0,
    sl_bps: 0,
    active_orders: [],
    active_order_count: 0,
    last_quote: null,
    loop_count: 0,
    consecutive_failures: 0,
    uptime: {
        current_hour: {
            maker_active_seconds: 0,
            mm_active_seconds: 0,
            total_elapsed_seconds: 0,
            maker_uptime_pct: 0,
            mm_uptime_pct: 0,
            target_seconds: 1800,
            maker_target_met: false,
            seconds_remaining_for_target: 1800,
            seconds_elapsed_in_hour: 0,
            is_active: false,
        },
        history: [],
        hours_target_met_last_24h: 0,
        avg_maker_uptime_pct_last_24h: 0,
        avg_mm_uptime_pct_last_24h: 0,
    },
    uptime_percentage: 0,
    mm_uptime_percentage: 0,
};

export function useWebSocket(url: string) {
    const [state, setState] = useState<BotState>(INITIAL_STATE);
    const [connected, setConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

    const connect = useCallback(() => {
        try {
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                setConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'state_update') {
                        setState(data as BotState);
                    }
                } catch {
                    // Ignore invalid JSON
                }
            };

            ws.onclose = () => {
                setConnected(false);
                reconnectTimeout.current = setTimeout(connect, 3000);
            };

            ws.onerror = () => {
                ws.close();
            };
        } catch {
            reconnectTimeout.current = setTimeout(connect, 3000);
        }
    }, [url]);

    useEffect(() => {
        connect();
        return () => {
            if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
            if (wsRef.current) wsRef.current.close();
        };
    }, [connect]);

    return { state, connected };
}
