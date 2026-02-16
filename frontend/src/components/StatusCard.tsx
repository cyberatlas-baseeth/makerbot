interface StatusCardProps {
    status: string;
    symbol: string;
    loopCount: number;
    consecutiveFailures: number;
    connected: boolean;
}

export default function StatusCard({ status, symbol, loopCount, consecutiveFailures, connected }: StatusCardProps) {
    const getBadgeClass = () => {
        switch (status) {
            case 'running': return 'badge-running';
            case 'paused': return 'badge-paused';
            case 'error':
            case 'killed': return 'badge-error';
            default: return 'badge-starting';
        }
    };

    const getDotClass = () => {
        switch (status) {
            case 'running': return 'pulse-dot-green';
            case 'paused': return 'pulse-dot-yellow';
            default: return 'pulse-dot-red';
        }
    };

    return (
        <div className="glass-card animate-fade-in">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold tracking-wider uppercase text-text-secondary">
                    Bot Status
                </h2>
                <div className="flex items-center gap-2">
                    <div className={`pulse-dot ${getDotClass()}`} />
                    <span className={`badge ${getBadgeClass()}`}>{status}</span>
                </div>
            </div>

            <div className="space-y-3">
                <div className="flex justify-between items-center">
                    <span className="text-text-muted text-xs">Symbol</span>
                    <span className="text-lg font-bold tracking-wide">{symbol}</span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-text-muted text-xs">Engine Loops</span>
                    <span className="font-mono text-sm">{loopCount.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-text-muted text-xs">Failures</span>
                    <span className={`font-mono text-sm ${consecutiveFailures > 0 ? 'num-red' : 'num-green'}`}>
                        {consecutiveFailures}
                    </span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-text-muted text-xs">WS Link</span>
                    <span className={`text-xs font-semibold ${connected ? 'num-green' : 'num-red'}`}>
                        {connected ? 'CONNECTED' : 'DISCONNECTED'}
                    </span>
                </div>
            </div>
        </div>
    );
}
