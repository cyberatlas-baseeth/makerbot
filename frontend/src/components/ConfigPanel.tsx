import { useState } from 'react';
import { updateConfig, killBot } from '../lib/api';

interface ConfigPanelProps {
    currentSpreadBps: number;
    currentOrderSize: number;
    currentRefreshInterval: number;
    botStatus: string;
}

export default function ConfigPanel({
    currentSpreadBps,
    currentOrderSize,
    currentRefreshInterval,
    botStatus,
}: ConfigPanelProps) {
    const [spreadBps, setSpreadBps] = useState('');
    const [orderSize, setOrderSize] = useState('');
    const [refreshInterval, setRefreshInterval] = useState('');
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');
    const [killing, setKilling] = useState(false);

    const handleSave = async () => {
        setSaving(true);
        setMessage('');
        try {
            const config: Record<string, number> = {};
            if (spreadBps) config.spread_bps = parseFloat(spreadBps);
            if (orderSize) config.order_size = parseFloat(orderSize);
            if (refreshInterval) config.refresh_interval = parseFloat(refreshInterval);

            if (Object.keys(config).length === 0) {
                setMessage('No changes to save');
                setSaving(false);
                return;
            }

            await updateConfig(config);
            setMessage('✓ Updated');
            setSpreadBps('');
            setOrderSize('');
            setRefreshInterval('');
        } catch {
            setMessage('✗ Failed to update');
        }
        setSaving(false);
        setTimeout(() => setMessage(''), 3000);
    };

    const handleKill = async () => {
        if (!window.confirm('⚠️ KILL SWITCH: This will cancel ALL orders and stop the bot. Continue?')) {
            return;
        }
        setKilling(true);
        try {
            await killBot();
        } catch {
            // Handled by status update
        }
        setKilling(false);
    };

    return (
        <div className="glass-card animate-fade-in" style={{ animationDelay: '0.25s' }}>
            <h2 className="text-sm font-semibold tracking-wider uppercase text-text-secondary mb-4">
                Configuration
            </h2>

            <div className="space-y-3">
                <div>
                    <label className="text-text-muted text-xs block mb-1">
                        Spread (bps) — current: {currentSpreadBps}
                    </label>
                    <input
                        type="number"
                        step="0.1"
                        className="config-input"
                        placeholder={currentSpreadBps.toString()}
                        value={spreadBps}
                        onChange={(e) => setSpreadBps(e.target.value)}
                    />
                </div>

                <div>
                    <label className="text-text-muted text-xs block mb-1">
                        Order Size — current: {currentOrderSize}
                    </label>
                    <input
                        type="number"
                        step="0.01"
                        className="config-input"
                        placeholder={currentOrderSize.toString()}
                        value={orderSize}
                        onChange={(e) => setOrderSize(e.target.value)}
                    />
                </div>

                <div>
                    <label className="text-text-muted text-xs block mb-1">
                        Refresh Interval (s) — current: {currentRefreshInterval}
                    </label>
                    <input
                        type="number"
                        step="1"
                        className="config-input"
                        placeholder={currentRefreshInterval.toString()}
                        value={refreshInterval}
                        onChange={(e) => setRefreshInterval(e.target.value)}
                    />
                </div>

                <div className="flex gap-2 pt-2">
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex-1 bg-accent hover:bg-accent-hover text-white py-2.5 rounded-lg text-sm font-semibold transition-all disabled:opacity-50 cursor-pointer"
                    >
                        {saving ? 'Saving...' : 'Update Config'}
                    </button>
                </div>

                {message && (
                    <p className={`text-xs text-center ${message.startsWith('✓') ? 'num-green' : message.startsWith('✗') ? 'num-red' : 'text-text-secondary'}`}>
                        {message}
                    </p>
                )}
            </div>

            <div className="mt-6 pt-4 border-t border-border">
                <button
                    onClick={handleKill}
                    disabled={killing || botStatus === 'killed'}
                    className="kill-button w-full disabled:opacity-40 disabled:cursor-not-allowed"
                >
                    {killing ? 'KILLING...' : botStatus === 'killed' ? 'BOT KILLED' : '⚡ KILL SWITCH'}
                </button>
                <p className="text-text-muted text-xs text-center mt-2">
                    Cancels all orders and stops the engine immediately
                </p>
            </div>
        </div>
    );
}
