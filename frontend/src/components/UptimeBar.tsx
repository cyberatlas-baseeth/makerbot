import type { UptimeStats, ClosedPosition } from '../hooks/useWebSocket';

interface UptimeBarProps {
    uptime: UptimeStats;
    closedPositions: ClosedPosition[];
}

function fmtTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}m ${s}s`;
}

function fmtAgo(timestamp: number): string {
    const diff = Math.floor(Date.now() / 1000 - timestamp);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
}

export default function UptimeBar({ uptime, closedPositions }: UptimeBarProps) {
    const { current_hour } = uptime;
    const makerPct = current_hour.maker_uptime_pct;
    const mmPct = current_hour.mm_uptime_pct;
    const targetPct = (current_hour.target_seconds / 3600) * 100;

    return (
        <div>
            <h3 className="heading-lg" style={{ marginBottom: '14px' }}>UPTIME TRACKING</h3>

            {/* Maker Uptime */}
            <div style={{ marginBottom: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '6px' }}>
                    <span className="metric-label" style={{ opacity: 1 }}>
                        MAKER (5 BPS)
                    </span>
                    <span style={{ fontSize: '1.2rem', fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
                        {makerPct.toFixed(1)}%
                    </span>
                </div>
                <div className="progress-track">
                    <div
                        className="progress-fill progress-fill-maker"
                        style={{ width: `${Math.min(makerPct, 100)}%` }}
                    />
                    {/* Target line */}
                    <div style={{
                        position: 'absolute',
                        left: `${targetPct}%`,
                        top: 0,
                        bottom: 0,
                        width: '2px',
                        background: '#111',
                        zIndex: 1,
                    }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                    <span style={{ fontSize: '0.6rem', fontWeight: 500, opacity: 0.5 }}>
                        {fmtTime(current_hour.maker_active_seconds)} ACTIVE
                    </span>
                    <span style={{ fontSize: '0.6rem', fontWeight: 500, opacity: 0.5 }}>
                        {current_hour.maker_target_met ? 'TARGET MET' : `${fmtTime(current_hour.seconds_remaining_for_target)} REMAINING`}
                    </span>
                </div>
            </div>

            {/* MM Uptime */}
            <div style={{ marginBottom: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '6px' }}>
                    <span className="metric-label" style={{ opacity: 1 }}>
                        MARKET MAKER (&gt;5 BPS)
                    </span>
                    <span style={{ fontSize: '1.2rem', fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
                        {mmPct.toFixed(1)}%
                    </span>
                </div>
                <div className="progress-track">
                    <div
                        className="progress-fill progress-fill-mm"
                        style={{ width: `${Math.min(mmPct, 100)}%` }}
                    />
                </div>
                <div style={{ marginTop: '4px' }}>
                    <span style={{ fontSize: '0.6rem', fontWeight: 500, opacity: 0.5 }}>
                        {fmtTime(current_hour.mm_active_seconds)} ACTIVE
                    </span>
                </div>
            </div>

            {/* Closed Positions */}
            {closedPositions.length > 0 && (
                <div>
                    <div className="metric-label" style={{ marginBottom: '8px', opacity: 1 }}>CLOSED POSITIONS</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '160px', overflowY: 'auto' }}>
                        {closedPositions.slice().reverse().map((pos, i) => (
                            <div
                                key={i}
                                style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: '6px 10px',
                                    background: pos.side === 'long' ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
                                    borderLeft: `3px solid ${pos.side === 'long' ? '#22c55e' : '#ef4444'}`,
                                    fontSize: '0.65rem',
                                    fontFamily: 'var(--font-mono)',
                                }}
                            >
                                <span style={{ color: pos.side === 'long' ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
                                    {pos.side.toUpperCase()} {pos.qty}
                                </span>
                                <span style={{ opacity: 0.7 }}>
                                    @ ${pos.entry_price.toLocaleString()}
                                </span>
                                <span style={{ opacity: 0.4 }}>
                                    {fmtAgo(pos.closed_at)}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
