import { useWebSocket } from '../hooks/useWebSocket';
import ControlPanel from './ConfigPanel';
import StatusCard from './StatusCard';
import UptimeBar from './UptimeBar';
import OrdersTable from './OrdersTable';

const WS_URL = 'ws://localhost:8000/ws';

export default function Dashboard() {
    const { state, connected } = useWebSocket(WS_URL);

    const statusDotClass = () => {
        switch (state.status) {
            case 'running': return 'status-dot-active';
            case 'stopped': return 'status-dot-idle';
            case 'paused': return 'status-dot-warning';
            default: return 'status-dot-inactive';
        }
    };

    const badgeClass = () => {
        switch (state.status) {
            case 'running': return 'badge-running';
            case 'stopped': return 'badge-stopped';
            case 'paused': return 'badge-paused';
            case 'error':
            case 'killed': return 'badge-error';
            default: return 'badge-starting';
        }
    };

    return (
        <div style={{ minHeight: '100vh', background: '#111111' }}>
            {/* 3-Panel Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: '280px 1fr 260px',
                minHeight: '100vh',
            }}>

                {/* ═══ LEFT PANEL — CONTROL (Yellow) ═══ */}
                <div className="panel panel-yellow" style={{ display: 'flex', flexDirection: 'column', borderRight: 'none' }}>
                    <ControlPanel
                        currentSymbol={state.symbol}
                        currentSpreadBps={state.configured_spread_bps}
                        currentBidNotional={state.bid_notional}
                        currentAskNotional={state.ask_notional}
                        currentRequoteBps={state.requote_threshold_bps}
                        currentTpBps={state.tp_bps}
                        currentSlBps={state.sl_bps}
                        botStatus={state.status}
                    />
                </div>

                {/* ═══ MIDDLE PANEL — ENGINE (Sage) ═══ */}
                <div className="panel panel-sage" style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                    {/* Engine Header */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
                        <h2 className="heading-lg">ENGINE STATUS</h2>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div className={`status-dot ${statusDotClass()}`} />
                            <span className={`status-badge ${badgeClass()}`}>{state.status}</span>
                        </div>
                    </div>

                    {/* Status + Pricing Grid */}
                    <StatusCard
                        symbol={state.symbol}
                        midPrice={state.mid_price}
                        bestBid={state.best_bid}
                        bestAsk={state.best_ask}
                        spreadBps={state.market_spread_bps}
                        configuredSpreadBps={state.configured_spread_bps}
                        lastQuote={state.last_quote}
                        bidSpreadBps={state.bid_spread_bps || state.configured_spread_bps}
                        askSpreadBps={state.ask_spread_bps || state.configured_spread_bps}
                    />

                    {/* Open Position Alert */}
                    {state.open_position && (
                        <div style={{
                            marginTop: '12px',
                            padding: '10px 14px',
                            background: state.open_position.side === 'long' ? '#1a3a1a' : '#3a1a1a',
                            border: `2px solid ${state.open_position.side === 'long' ? '#22c55e' : '#ef4444'}`,
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                        }}>
                            <span style={{ color: state.open_position.side === 'long' ? '#22c55e' : '#ef4444', fontWeight: 700, fontFamily: 'var(--font-mono)', fontSize: '12px', letterSpacing: '0.05em' }}>
                                ⚠ OPEN {state.open_position.side.toUpperCase()} POSITION
                            </span>
                            <span style={{ color: '#E6E4D8', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                                {state.open_position.qty} @ ${state.open_position.entry_price.toLocaleString()}
                            </span>
                        </div>
                    )}

                    {/* Uptime */}
                    <div style={{ marginTop: '20px' }}>
                        <UptimeBar uptime={state.uptime} />
                    </div>

                    {/* Orders Table */}
                    <div style={{ marginTop: '20px', flex: 1 }}>
                        <OrdersTable orders={state.active_orders} />
                    </div>
                </div>

                {/* ═══ RIGHT PANEL — RISK (Orange) ═══ */}
                <div className="panel panel-orange" style={{ display: 'flex', flexDirection: 'column', borderLeft: 'none' }}>
                    <h2 className="heading-lg" style={{ marginBottom: '20px', color: '#E6E4D8' }}>
                        RISK / METRICS
                    </h2>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {/* Active Orders */}
                        <div className="metric-block metric-block-light">
                            <div className="metric-label" style={{ marginBottom: '6px', color: 'rgba(230,228,216,0.6)' }}>
                                ACTIVE ORDERS
                            </div>
                            <div className="metric-value" style={{ color: '#E6E4D8' }}>
                                {state.active_order_count}
                            </div>
                        </div>

                        {/* Loop Count */}
                        <div className="metric-block metric-block-light">
                            <div className="metric-label" style={{ marginBottom: '6px', color: 'rgba(230,228,216,0.6)' }}>
                                LOOP COUNT
                            </div>
                            <div className="metric-value" style={{ color: '#E6E4D8' }}>
                                {state.loop_count.toLocaleString()}
                            </div>
                        </div>

                        {/* WS Status */}
                        <div className="metric-block metric-block-light">
                            <div className="metric-label" style={{ marginBottom: '6px', color: 'rgba(230,228,216,0.6)' }}>
                                WEBSOCKET
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <div className={`status-dot ${connected ? 'status-dot-active' : 'status-dot-inactive'}`} />
                                <span className="metric-value" style={{ fontSize: '1rem', color: '#E6E4D8' }}>
                                    {connected ? 'CONNECTED' : 'DISCONNECTED'}
                                </span>
                            </div>
                        </div>

                        {/* Consecutive Failures */}
                        <div className="metric-block metric-block-light">
                            <div className="metric-label" style={{ marginBottom: '6px', color: 'rgba(230,228,216,0.6)' }}>
                                FAILURES
                            </div>
                            <div className="metric-value" style={{
                                color: state.consecutive_failures > 0 ? '#fff' : '#E6E4D8'
                            }}>
                                {state.consecutive_failures}
                            </div>
                        </div>

                        {/* Refresh Interval */}
                        <div className="metric-block metric-block-light">
                            <div className="metric-label" style={{ marginBottom: '6px', color: 'rgba(230,228,216,0.6)' }}>
                                REFRESH
                            </div>
                            <div className="metric-value" style={{ color: '#E6E4D8' }}>
                                {state.refresh_interval}s
                            </div>
                        </div>

                        {/* Uptime Summary */}
                        <div className="metric-block metric-block-light">
                            <div className="metric-label" style={{ marginBottom: '6px', color: 'rgba(230,228,216,0.6)' }}>
                                MAKER UPTIME
                            </div>
                            <div className="metric-value" style={{ color: '#E6E4D8' }}>
                                {state.uptime_percentage.toFixed(1)}%
                            </div>
                        </div>

                        <div className="metric-block metric-block-light">
                            <div className="metric-label" style={{ marginBottom: '6px', color: 'rgba(230,228,216,0.6)' }}>
                                MM UPTIME
                            </div>
                            <div className="metric-value" style={{ color: '#E6E4D8' }}>
                                {state.mm_uptime_percentage.toFixed(1)}%
                            </div>
                        </div>
                    </div>

                    {/* Version footer */}
                    <div style={{ marginTop: 'auto', paddingTop: '24px' }}>
                        <hr className="divider" style={{ borderColor: 'rgba(230,228,216,0.2)' }} />
                        <div style={{ fontSize: '0.65rem', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(230,228,216,0.4)' }}>
                            MAKERBOT V2.0.0
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
