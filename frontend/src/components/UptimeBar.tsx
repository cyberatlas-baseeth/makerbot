import type { UptimeStats } from '../hooks/useWebSocket';

interface UptimeBarProps {
    uptime: UptimeStats;
}

function fmtTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}m ${s}s`;
}

export default function UptimeBar({ uptime }: UptimeBarProps) {
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
        </div>
    );
}

