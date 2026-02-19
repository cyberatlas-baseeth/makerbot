import { useWebSocket } from '../hooks/useWebSocket';
import StatusCard from './StatusCard';
import SpreadCard from './SpreadCard';
import UptimeBar from './UptimeBar';
import OrdersTable from './OrdersTable';
import ControlPanel from './ConfigPanel';

// Hardcoded localhost — this bot runs locally only
const WS_URL = 'ws://localhost:8000/ws';

export default function Dashboard() {
    const { state, connected } = useWebSocket(WS_URL);

    return (
        <div className="min-h-screen bg-bg-primary">
            {/* Header */}
            <header className="border-b border-border bg-[rgba(10,14,26,0.95)] backdrop-blur-xl sticky top-0 z-50">
                <div className="max-w-[1440px] mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent to-[#8b5cf6] flex items-center justify-center">
                            <span className="text-white font-bold text-sm">MM</span>
                        </div>
                        <div>
                            <h1 className="text-lg font-bold tracking-tight">Market Maker</h1>
                            <p className="text-text-muted text-xs">Uptime Optimized Quoting Engine</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <div className={`pulse-dot ${connected ? 'pulse-dot-green' : 'pulse-dot-red'}`} />
                            <span className="text-xs text-text-secondary">
                                {connected ? 'Live' : 'Reconnecting...'}
                            </span>
                        </div>
                        <span className="text-xs text-text-muted font-mono bg-bg-secondary px-3 py-1.5 rounded-lg border border-border">
                            {state.symbol}
                        </span>
                    </div>
                </div>
            </header>

            {/* Main Grid */}
            <main className="max-w-[1440px] mx-auto px-6 py-6">
                {/* Top Row: Control Panel + Status + Spread */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">
                    <ControlPanel
                        currentSymbol={state.symbol}
                        currentSpreadBps={state.configured_spread_bps}
                        currentBidNotional={state.bid_notional}
                        currentAskNotional={state.ask_notional}
                        currentRequoteUsd={state.requote_threshold_usd}
                        botStatus={state.status}
                    />
                    <StatusCard
                        status={state.status}
                        symbol={state.symbol}
                        midPrice={state.mid_price}
                        bestBid={state.best_bid}
                        bestAsk={state.best_ask}
                        spreadBps={state.market_spread_bps}
                        activeOrderCount={state.active_order_count}
                        connected={connected}
                    />
                    <SpreadCard
                        midPrice={state.mid_price}
                        marketSpreadBps={state.market_spread_bps}
                        configuredSpreadBps={state.configured_spread_bps}
                        lastQuote={state.last_quote}
                        bidSpreadBps={state.bid_spread_bps || state.configured_spread_bps}
                        askSpreadBps={state.ask_spread_bps || state.configured_spread_bps}
                    />
                </div>

                {/* Uptime Bar — full width */}
                <div className="mb-5">
                    <UptimeBar uptime={state.uptime} />
                </div>

                {/* Orders — full width */}
                <div>
                    <OrdersTable orders={state.active_orders} />
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-border mt-8 py-4">
                <div className="max-w-[1440px] mx-auto px-6 flex justify-between text-xs text-text-muted">
                    <span>Market Maker Bot v2.0.0 — Local Only</span>
                    <span className="font-mono">
                        Loop #{state.loop_count} | Refresh: {state.refresh_interval}s
                    </span>
                </div>
            </footer>
        </div>
    );
}
