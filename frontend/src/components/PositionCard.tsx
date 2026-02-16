import type { RiskStatus } from '../hooks/useWebSocket';

interface PositionCardProps {
    risk: RiskStatus;
}

export default function PositionCard({ risk }: PositionCardProps) {
    const { position } = risk;
    const totalPnl = position.unrealized_pnl + position.realized_pnl;

    const fmtUsd = (n: number) =>
        n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    return (
        <div className="glass-card animate-fade-in" style={{ animationDelay: '0.2s' }}>
            <h2 className="text-sm font-semibold tracking-wider uppercase text-text-secondary mb-4">
                Position & PnL
            </h2>

            <div className="text-center mb-4">
                <span className="text-text-muted text-xs block mb-1">Net Position</span>
                <span className={`text-2xl font-bold font-mono ${position.size > 0 ? 'num-green' : position.size < 0 ? 'num-red' : ''}`}>
                    {position.size > 0 ? '+' : ''}{position.size.toFixed(4)}
                </span>
            </div>

            <div className="space-y-2.5">
                <div className="flex justify-between">
                    <span className="text-text-muted text-xs">Avg Entry</span>
                    <span className="font-mono text-sm">${fmtUsd(position.avg_entry)}</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-text-muted text-xs">Notional</span>
                    <span className="font-mono text-sm">${fmtUsd(position.notional)}</span>
                </div>

                <div className="border-t border-border my-2" />

                <div className="flex justify-between">
                    <span className="text-text-muted text-xs">Unrealized PnL</span>
                    <span className={`font-mono text-sm font-semibold ${position.unrealized_pnl >= 0 ? 'num-green' : 'num-red'}`}>
                        {position.unrealized_pnl >= 0 ? '+' : ''}${fmtUsd(position.unrealized_pnl)}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-text-muted text-xs">Realized PnL</span>
                    <span className={`font-mono text-sm ${position.realized_pnl >= 0 ? 'num-green' : 'num-red'}`}>
                        {position.realized_pnl >= 0 ? '+' : ''}${fmtUsd(position.realized_pnl)}
                    </span>
                </div>
                <div className="flex justify-between items-center pt-1">
                    <span className="text-text-muted text-xs font-semibold">Total PnL</span>
                    <span className={`font-mono text-lg font-bold ${totalPnl >= 0 ? 'num-green' : 'num-red'}`}>
                        {totalPnl >= 0 ? '+' : ''}${fmtUsd(totalPnl)}
                    </span>
                </div>

                <div className="border-t border-border my-2" />

                {/* Utilization bars */}
                <div>
                    <div className="flex justify-between text-xs text-text-muted mb-1">
                        <span>Position Util.</span>
                        <span>{risk.position_utilization.toFixed(1)}%</span>
                    </div>
                    <div className="progress-outer" style={{ height: '6px' }}>
                        <div
                            className="progress-inner"
                            style={{
                                width: `${Math.min(risk.position_utilization, 100)}%`,
                                background: risk.position_utilization > 80
                                    ? 'linear-gradient(90deg, #ef4444, #f87171)'
                                    : 'linear-gradient(90deg, #3b82f6, #60a5fa)',
                            }}
                        />
                    </div>
                </div>
                <div>
                    <div className="flex justify-between text-xs text-text-muted mb-1">
                        <span>Notional Util.</span>
                        <span>{risk.notional_utilization.toFixed(1)}%</span>
                    </div>
                    <div className="progress-outer" style={{ height: '6px' }}>
                        <div
                            className="progress-inner"
                            style={{
                                width: `${Math.min(risk.notional_utilization, 100)}%`,
                                background: risk.notional_utilization > 80
                                    ? 'linear-gradient(90deg, #ef4444, #f87171)'
                                    : 'linear-gradient(90deg, #3b82f6, #60a5fa)',
                            }}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
