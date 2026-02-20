import type { Quote } from '../hooks/useWebSocket';

interface StatusCardProps {
    symbol: string;
    midPrice: number | null;
    bestBid: number | null;
    bestAsk: number | null;
    spreadBps: number | null;
    configuredSpreadBps: number;
    lastQuote: Quote | null;
    bidSpreadBps: number;
    askSpreadBps: number;
}

function formatPrice(price: number | null): string {
    if (price === null || price === undefined) return '---';
    if (price >= 1000) return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (price >= 1) return price.toFixed(4);
    return price.toFixed(8);
}

export default function StatusCard({
    symbol,
    midPrice,
    bestBid,
    bestAsk,
    spreadBps,
    configuredSpreadBps,
    lastQuote,
    bidSpreadBps,
    askSpreadBps,
}: StatusCardProps) {
    const effectiveBidSpread = bidSpreadBps || configuredSpreadBps;
    const effectiveAskSpread = askSpreadBps || configuredSpreadBps;
    const displayBid = midPrice ? midPrice * (1 - effectiveBidSpread / 10000) : null;
    const displayAsk = midPrice ? midPrice * (1 + effectiveAskSpread / 10000) : null;

    return (
        <div>
            {/* Mid Price — hero metric */}
            <div className="metric-block metric-block-dark" style={{ marginBottom: '12px', textAlign: 'center', padding: '20px' }}>
                <div className="metric-label" style={{ marginBottom: '8px' }}>
                    MID PRICE — {symbol}
                </div>
                <div className="metric-value-lg">
                    ${formatPrice(midPrice)}
                </div>
            </div>

            {/* 2x3 Metric Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                {/* Best Bid */}
                <div className="metric-block metric-block-dark">
                    <div className="metric-label" style={{ marginBottom: '6px' }}>BEST BID</div>
                    <div className="metric-value" style={{ color: '#0F2F3A' }}>
                        ${formatPrice(bestBid)}
                    </div>
                </div>

                {/* Best Ask */}
                <div className="metric-block metric-block-dark">
                    <div className="metric-label" style={{ marginBottom: '6px' }}>BEST ASK</div>
                    <div className="metric-value" style={{ color: '#0F2F3A' }}>
                        ${formatPrice(bestAsk)}
                    </div>
                </div>

                {/* Our Bid */}
                <div className="metric-block metric-block-dark" style={{ background: 'rgba(15,47,58,0.1)' }}>
                    <div className="metric-label" style={{ marginBottom: '6px' }}>OUR BID</div>
                    <div className="metric-value" style={{ fontSize: '1.1rem', color: '#0F2F3A' }}>
                        ${formatPrice(displayBid)}
                    </div>
                    <div style={{ fontSize: '0.65rem', fontWeight: 600, opacity: 0.5, marginTop: '4px' }}>
                        -{effectiveBidSpread.toFixed(1)} BPS
                    </div>
                </div>

                {/* Our Ask */}
                <div className="metric-block metric-block-dark" style={{ background: 'rgba(15,47,58,0.1)' }}>
                    <div className="metric-label" style={{ marginBottom: '6px' }}>OUR ASK</div>
                    <div className="metric-value" style={{ fontSize: '1.1rem', color: '#0F2F3A' }}>
                        ${formatPrice(displayAsk)}
                    </div>
                    <div style={{ fontSize: '0.65rem', fontWeight: 600, opacity: 0.5, marginTop: '4px' }}>
                        +{effectiveAskSpread.toFixed(1)} BPS
                    </div>
                </div>

                {/* Market Spread */}
                <div className="metric-block metric-block-dark">
                    <div className="metric-label" style={{ marginBottom: '6px' }}>MARKET SPREAD</div>
                    <div className="metric-value" style={{ color: '#0F2F3A' }}>
                        {spreadBps !== null ? `${spreadBps.toFixed(2)}` : '---'}
                        <span style={{ fontSize: '0.75rem', fontWeight: 500, opacity: 0.6 }}> BPS</span>
                    </div>
                </div>

                {/* Configured Spread */}
                <div className="metric-block metric-block-dark">
                    <div className="metric-label" style={{ marginBottom: '6px' }}>CONFIG SPREAD</div>
                    <div className="metric-value" style={{ color: '#0F2F3A' }}>
                        {configuredSpreadBps.toFixed(1)}
                        <span style={{ fontSize: '0.75rem', fontWeight: 500, opacity: 0.6 }}> BPS</span>
                    </div>
                </div>
            </div>

            {/* Quote Sizes */}
            {lastQuote && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '10px' }}>
                    <div className="metric-block metric-block-dark" style={{ padding: '10px 14px' }}>
                        <div className="metric-label" style={{ marginBottom: '4px' }}>BID QTY</div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                            {lastQuote.bid_size.toFixed(6)}
                        </div>
                    </div>
                    <div className="metric-block metric-block-dark" style={{ padding: '10px 14px' }}>
                        <div className="metric-label" style={{ marginBottom: '4px' }}>ASK QTY</div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                            {lastQuote.ask_size.toFixed(6)}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
