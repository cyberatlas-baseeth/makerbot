interface StatusCardProps {
    status: string;
    symbol: string;
    midPrice: number | null;
    bestBid: number | null;
    bestAsk: number | null;
    spreadBps: number | null;
    activeOrderCount: number;
    connected: boolean;
}

function formatPrice(price: number | null): string {
    if (price === null || price === undefined) return '—';
    if (price >= 1000) return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (price >= 1) return price.toFixed(4);
    return price.toFixed(8);
}

export default function StatusCard({
    status,
    symbol,
    midPrice,
    bestBid,
    bestAsk,
    spreadBps,
    activeOrderCount,
    connected,
}: StatusCardProps) {
    const getBadgeClass = () => {
        switch (status) {
            case 'running': return 'badge-running';
            case 'stopped': return 'badge-stopped';
            case 'paused': return 'badge-paused';
            case 'error':
            case 'killed': return 'badge-error';
            default: return 'badge-starting';
        }
    };

    const getDotClass = () => {
        switch (status) {
            case 'running': return 'pulse-dot-green';
            case 'stopped': return 'pulse-dot-gray';
            case 'paused': return 'pulse-dot-yellow';
            default: return 'pulse-dot-red';
        }
    };

    return (
        <div className="glass-card animate-fade-in">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold tracking-wider uppercase text-text-secondary">
                    Market Status
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
                    <span className="text-text-muted text-xs">Mid Price</span>
                    <span className="font-mono text-base font-semibold">{formatPrice(midPrice)}</span>
                </div>

                <div className="flex justify-between items-center">
                    <span className="text-text-muted text-xs">Best Bid</span>
                    <span className="font-mono text-sm num-green">{formatPrice(bestBid)}</span>
                </div>

                <div className="flex justify-between items-center">
                    <span className="text-text-muted text-xs">Best Ask</span>
                    <span className="font-mono text-sm num-red">{formatPrice(bestAsk)}</span>
                </div>

                <div className="flex justify-between items-center">
                    <span className="text-text-muted text-xs">Spread</span>
                    <span className="font-mono text-sm text-text-secondary">
                        {spreadBps !== null && spreadBps !== undefined ? `${spreadBps.toFixed(2)} bps` : '—'}
                    </span>
                </div>

                <div className="flex justify-between items-center">
                    <span className="text-text-muted text-xs">Active Orders</span>
                    <span className={`font-mono text-sm font-semibold ${activeOrderCount > 0 ? 'num-green' : 'text-text-muted'}`}>
                        {activeOrderCount}
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
