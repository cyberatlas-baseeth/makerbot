import type { Quote } from '../hooks/useWebSocket';

interface SpreadCardProps {
    midPrice: number | null;
    marketSpreadBps: number | null;
    configuredSpreadBps: number;
    lastQuote: Quote | null;
}

export default function SpreadCard({ midPrice, marketSpreadBps, configuredSpreadBps, lastQuote }: SpreadCardProps) {
    const fmt = (n: number | null | undefined, decimals = 2) =>
        n != null ? n.toFixed(decimals) : '—';

    const fmtPrice = (n: number | null | undefined) =>
        n != null ? n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 }) : '—';

    return (
        <div className="glass-card animate-fade-in" style={{ animationDelay: '0.05s' }}>
            <h2 className="text-sm font-semibold tracking-wider uppercase text-text-secondary mb-4">
                Pricing
            </h2>

            <div className="text-center mb-5">
                <span className="text-text-muted text-xs block mb-1">Mid Price</span>
                <span className="text-3xl font-bold tracking-tight">
                    ${fmtPrice(midPrice)}
                </span>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="rounded-xl bg-[rgba(16,185,129,0.08)] border border-[rgba(16,185,129,0.2)] p-3 text-center">
                    <span className="text-text-muted text-xs block mb-1">Bid</span>
                    <span className="num-green text-lg font-bold font-mono">
                        ${fmtPrice(lastQuote?.bid_price)}
                    </span>
                </div>
                <div className="rounded-xl bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] p-3 text-center">
                    <span className="text-text-muted text-xs block mb-1">Ask</span>
                    <span className="num-red text-lg font-bold font-mono">
                        ${fmtPrice(lastQuote?.ask_price)}
                    </span>
                </div>
            </div>

            <div className="space-y-2">
                <div className="flex justify-between">
                    <span className="text-text-muted text-xs">Market Spread</span>
                    <span className="font-mono text-sm">{fmt(marketSpreadBps)} bps</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-text-muted text-xs">Configured Spread</span>
                    <span className="font-mono text-sm">{fmt(configuredSpreadBps)} bps</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-text-muted text-xs">Quote Spread</span>
                    <span className="font-mono text-sm">{fmt(lastQuote?.spread_bps)} bps</span>
                </div>
                {lastQuote && (
                    <div className="flex justify-between">
                        <span className="text-text-muted text-xs">Within Limits</span>
                        <span className={`text-xs font-semibold ${lastQuote.within_limits ? 'num-green' : 'num-red'}`}>
                            {lastQuote.within_limits ? '✓ YES' : '✗ NO'}
                        </span>
                    </div>
                )}
            </div>
        </div>
    );
}
