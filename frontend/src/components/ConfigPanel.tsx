import { useState, useCallback } from 'react';
import { startBot, stopBot, updateConfig, killBot } from '../lib/api';

const SUPPORTED_SYMBOLS = ['BTC-USD', 'ETH-USD', 'XAU-USD', 'XAG-USD'];

interface ControlPanelProps {
    currentSymbol: string;
    currentSpreadBps: number;
    currentOrderSize: number;
    botStatus: string;
}

export default function ControlPanel({
    currentSymbol,
    currentSpreadBps,
    currentOrderSize,
    botStatus,
}: ControlPanelProps) {
    const [selectedSymbol, setSelectedSymbol] = useState('');
    const [spreadBps, setSpreadBps] = useState('');
    const [orderSize, setOrderSize] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [killing, setKilling] = useState(false);

    const isRunning = botStatus === 'running';
    const isStopped = botStatus === 'stopped' || botStatus === 'killed' || botStatus === 'error';

    const showMessage = useCallback((msg: string) => {
        setMessage(msg);
        setTimeout(() => setMessage(''), 4000);
    }, []);

    const handleStart = async () => {
        if (loading) return;
        setLoading(true);
        try {
            await startBot();
            showMessage('✓ Engine started');
        } catch (err: any) {
            showMessage(`✗ ${err.message || 'Failed to start'}`);
        }
        setLoading(false);
    };

    const handleStop = async () => {
        if (loading) return;
        setLoading(true);
        try {
            await stopBot();
            showMessage('✓ Engine stopped');
        } catch (err: any) {
            showMessage(`✗ ${err.message || 'Failed to stop'}`);
        }
        setLoading(false);
    };

    const handleApplyConfig = async () => {
        if (loading) return;
        setLoading(true);
        setMessage('');
        try {
            const config: Record<string, any> = {};
            const effectiveSymbol = selectedSymbol || currentSymbol;

            if (selectedSymbol && selectedSymbol !== currentSymbol) {
                config.symbol = selectedSymbol;
            }
            if (spreadBps) config.spread_bps = parseFloat(spreadBps);
            if (orderSize) config.order_size = parseFloat(orderSize);

            if (Object.keys(config).length === 0) {
                showMessage('No changes to apply');
                setLoading(false);
                return;
            }

            await updateConfig(config);
            showMessage(config.symbol ? `✓ Switched to ${effectiveSymbol}` : '✓ Config updated');
            setSpreadBps('');
            setOrderSize('');
            if (config.symbol) setSelectedSymbol('');
        } catch (err: any) {
            showMessage(`✗ ${err.message || 'Failed to update'}`);
        }
        setLoading(false);
    };

    const handleKill = async () => {
        if (!window.confirm('⚠️ KILL SWITCH: This will cancel ALL orders and stop the bot. Continue?')) {
            return;
        }
        setKilling(true);
        try {
            await killBot();
            showMessage('⚡ Kill switch activated');
        } catch {
            showMessage('✗ Kill failed');
        }
        setKilling(false);
    };

    return (
        <div className="glass-card animate-fade-in" style={{ animationDelay: '0.05s' }}>
            <h2 className="text-sm font-semibold tracking-wider uppercase text-text-secondary mb-5">
                Control Panel
            </h2>

            {/* Pair Selector */}
            <div className="mb-4">
                <label className="text-text-muted text-xs block mb-1.5">
                    Trading Pair — active: <span className="text-text-primary font-semibold">{currentSymbol}</span>
                </label>
                <select
                    className="select-dropdown"
                    value={selectedSymbol || currentSymbol}
                    onChange={(e) => setSelectedSymbol(e.target.value === currentSymbol ? '' : e.target.value)}
                    disabled={loading}
                >
                    {SUPPORTED_SYMBOLS.map((s) => (
                        <option key={s} value={s}>{s}</option>
                    ))}
                </select>
            </div>

            {/* Spread & Order Size */}
            <div className="grid grid-cols-2 gap-3 mb-4">
                <div>
                    <label className="text-text-muted text-xs block mb-1.5">
                        Spread (bps): <span className="text-text-secondary">{currentSpreadBps}</span>
                    </label>
                    <input
                        type="number"
                        step="0.1"
                        min="0.1"
                        className="config-input"
                        placeholder={currentSpreadBps.toString()}
                        value={spreadBps}
                        onChange={(e) => setSpreadBps(e.target.value)}
                        disabled={loading}
                    />
                </div>
                <div>
                    <label className="text-text-muted text-xs block mb-1.5">
                        Order Size: <span className="text-text-secondary">{currentOrderSize}</span>
                    </label>
                    <input
                        type="number"
                        step="0.01"
                        min="0.01"
                        className="config-input"
                        placeholder={currentOrderSize.toString()}
                        value={orderSize}
                        onChange={(e) => setOrderSize(e.target.value)}
                        disabled={loading}
                    />
                </div>
            </div>

            {/* Apply Config */}
            <button
                onClick={handleApplyConfig}
                disabled={loading}
                className="w-full bg-accent hover:bg-accent-hover text-white py-2.5 rounded-lg text-sm font-semibold transition-all disabled:opacity-50 cursor-pointer mb-4"
            >
                {loading && (selectedSymbol && selectedSymbol !== currentSymbol) ? (
                    <span className="flex items-center justify-center gap-2">
                        <span className="spinner" /> Switching...
                    </span>
                ) : (
                    'Apply Config'
                )}
            </button>

            {/* Start / Stop */}
            <div className="flex gap-3 mb-4">
                <button
                    id="btn-start"
                    onClick={handleStart}
                    disabled={isRunning || loading}
                    className="btn-start flex-1 flex items-center justify-center gap-2"
                >
                    {loading && !isRunning ? <span className="spinner" /> : '▶'}
                    START
                </button>
                <button
                    id="btn-stop"
                    onClick={handleStop}
                    disabled={isStopped || loading}
                    className="btn-stop flex-1 flex items-center justify-center gap-2"
                >
                    {loading && isRunning ? <span className="spinner" /> : '■'}
                    STOP
                </button>
            </div>

            {/* Message */}
            {message && (
                <p className={`text-xs text-center mb-3 ${message.startsWith('✓') ? 'num-green' : message.startsWith('✗') ? 'num-red' : 'text-warning'}`}>
                    {message}
                </p>
            )}

            {/* Kill Switch — collapsed danger zone */}
            <div className="pt-3 border-t border-border">
                <button
                    onClick={handleKill}
                    disabled={killing || botStatus === 'killed'}
                    className="kill-button w-full disabled:opacity-40 disabled:cursor-not-allowed"
                >
                    {killing ? 'KILLING...' : botStatus === 'killed' ? 'BOT KILLED' : '⚡ KILL SWITCH'}
                </button>
                <p className="text-text-muted text-xs text-center mt-2">
                    Emergency: cancels all orders and stops engine
                </p>
            </div>
        </div>
    );
}
