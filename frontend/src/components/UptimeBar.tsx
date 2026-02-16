import type { UptimeStats } from '../hooks/useWebSocket';

interface UptimeBarProps {
    uptime: UptimeStats;
}

export default function UptimeBar({ uptime }: UptimeBarProps) {
    const { current_hour } = uptime;
    const pct = Math.min(current_hour.uptime_pct, 100);
    const targetPct = (current_hour.target_seconds / 3600) * 100; // 50% for 30 min

    const getBarColor = () => {
        if (current_hour.target_met) return 'linear-gradient(90deg, #10b981, #34d399)';
        if (pct >= targetPct * 0.7) return 'linear-gradient(90deg, #f59e0b, #fbbf24)';
        return 'linear-gradient(90deg, #ef4444, #f87171)';
    };

    const fmtTime = (seconds: number) => {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}m ${s}s`;
    };

    return (
        <div className="glass-card animate-fade-in" style={{ animationDelay: '0.1s' }}>
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold tracking-wider uppercase text-text-secondary">
                    Maker Uptime
                </h2>
                <span className={`badge ${current_hour.target_met ? 'badge-running' : 'badge-paused'}`}>
                    {current_hour.target_met ? 'TARGET MET' : 'IN PROGRESS'}
                </span>
            </div>

            {/* Main progress bar */}
            <div className="mb-3">
                <div className="flex justify-between text-xs text-text-muted mb-1.5">
                    <span>Active: {fmtTime(current_hour.total_active_seconds)}</span>
                    <span>{pct.toFixed(1)}%</span>
                </div>
                <div className="progress-outer relative">
                    {/* Target marker line */}
                    <div
                        className="absolute top-0 bottom-0 w-0.5 bg-text-muted z-10 opacity-60"
                        style={{ left: `${targetPct}%` }}
                    />
                    <div
                        className="progress-inner"
                        style={{
                            width: `${pct}%`,
                            background: getBarColor(),
                        }}
                    />
                </div>
                <div className="flex justify-between text-xs text-text-muted mt-1">
                    <span>0m</span>
                    <span className="text-text-secondary font-semibold">Target: {(current_hour.target_seconds / 60).toFixed(0)}m</span>
                    <span>60m</span>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mt-4">
                <div className="rounded-lg bg-[rgba(15,23,42,0.6)] p-3 text-center">
                    <span className="text-text-muted text-xs block mb-1">Remaining for Target</span>
                    <span className="text-lg font-bold font-mono">
                        {fmtTime(current_hour.seconds_remaining_for_target)}
                    </span>
                </div>
                <div className="rounded-lg bg-[rgba(15,23,42,0.6)] p-3 text-center">
                    <span className="text-text-muted text-xs block mb-1">Hour Elapsed</span>
                    <span className="text-lg font-bold font-mono">
                        {fmtTime(current_hour.seconds_elapsed_in_hour)}
                    </span>
                </div>
            </div>

            {/* Activity indicator */}
            <div className="flex items-center gap-2 mt-4 text-xs">
                <div className={`pulse-dot ${current_hour.is_active ? 'pulse-dot-green' : 'pulse-dot-red'}`} />
                <span className="text-text-secondary">
                    {current_hour.is_active ? 'Actively quoting (both sides)' : 'Not actively quoting'}
                </span>
            </div>

            {/* 24h history */}
            {uptime.history.length > 0 && (
                <div className="mt-4 pt-3 border-t border-border">
                    <div className="flex justify-between text-xs text-text-muted mb-2">
                        <span>Last 24h: {uptime.hours_target_met_last_24h} hours met</span>
                        <span>Avg: {uptime.avg_uptime_pct_last_24h.toFixed(1)}%</span>
                    </div>
                    <div className="flex gap-0.5">
                        {uptime.history.map((h, i) => (
                            <div
                                key={i}
                                className="flex-1 h-3 rounded-sm"
                                style={{
                                    background: h.target_met
                                        ? 'rgba(16, 185, 129, 0.6)'
                                        : 'rgba(239, 68, 68, 0.3)',
                                }}
                                title={`${h.uptime_pct.toFixed(1)}% — ${h.target_met ? 'Met' : 'Missed'}`}
                            />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
