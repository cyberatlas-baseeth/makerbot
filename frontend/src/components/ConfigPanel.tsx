import { useState, useCallback } from 'react';
import { startBot, stopBot, updateConfig } from '../lib/api';

const SUPPORTED_SYMBOLS = ['BTC-USD', 'ETH-USD', 'XAU-USD', 'XAG-USD'];

interface ControlPanelProps {
    currentSymbol: string;
    currentSpreadBps: number;
    currentBidNotional: number;
    currentAskNotional: number;
    currentRequoteBps: number;
    botStatus: string;
}

export default function ControlPanel({
    currentSymbol,
    currentSpreadBps,
    currentBidNotional,
    currentAskNotional,
    currentRequoteBps,
    botStatus,
}: ControlPanelProps) {
    const [selectedSymbol, setSelectedSymbol] = useState('');
    const [spreadBps, setSpreadBps] = useState('');
    const [bidNotional, setBidNotional] = useState('');
    const [askNotional, setAskNotional] = useState('');
    const [requoteBps, setRequoteBps] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');

    const isRunning = botStatus === 'running';
    const isStopped = botStatus === 'stopped' || botStatus === 'error';

    const showMessage = useCallback((msg: string) => {
        setMessage(msg);
        setTimeout(() => setMessage(''), 4000);
    }, []);

    const handleStart = async () => {
        if (loading) return;
        setLoading(true);
        try {
            await startBot();
            showMessage('ENGINE STARTED');
        } catch (err: any) {
            showMessage(`ERROR: ${err.message || 'Failed'}`);
        }
        setLoading(false);
    };

    const handleStop = async () => {
        if (loading) return;
        setLoading(true);
        try {
            await stopBot();
            showMessage('ENGINE STOPPED');
        } catch (err: any) {
            showMessage(`ERROR: ${err.message || 'Failed'}`);
        }
        setLoading(false);
    };

    const handleApplyConfig = async () => {
        if (loading) return;
        setLoading(true);
        setMessage('');
        try {
            const config: Record<string, any> = {};
            if (selectedSymbol && selectedSymbol !== currentSymbol) {
                config.symbol = selectedSymbol;
            }
            if (spreadBps) config.spread_bps = parseFloat(spreadBps);
            if (bidNotional) config.bid_notional = parseFloat(bidNotional);
            if (askNotional) config.ask_notional = parseFloat(askNotional);
            if (requoteBps) config.requote_threshold_bps = parseFloat(requoteBps);

            if (Object.keys(config).length === 0) {
                showMessage('NO CHANGES');
                setLoading(false);
                return;
            }

            await updateConfig(config);
            showMessage(config.symbol ? `SWITCHED: ${config.symbol}` : 'CONFIG UPDATED');
            setSpreadBps('');
            setBidNotional('');
            setAskNotional('');
            setRequoteBps('');
            if (config.symbol) setSelectedSymbol('');
        } catch (err: any) {
            showMessage(`ERROR: ${err.message || 'Failed'}`);
        }
        setLoading(false);
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Title */}
            <h1 className="heading-xl" style={{ marginBottom: '4px' }}>MAKER</h1>
            <h1 className="heading-xl" style={{ marginBottom: '16px' }}>BOT</h1>
            <div style={{ fontSize: '0.65rem', fontWeight: 600, letterSpacing: '0.15em', textTransform: 'uppercase', opacity: 0.5, marginBottom: '24px' }}>
                UPTIME OPTIMIZED QUOTING
            </div>

            <hr className="divider divider-strong" style={{ borderColor: 'rgba(0,0,0,0.2)' }} />

            {/* Symbol */}
            <div style={{ marginBottom: '14px' }}>
                <label className="metric-label" style={{ display: 'block', marginBottom: '6px', opacity: 1, color: 'rgba(0,0,0,0.6)' }}>
                    SYMBOL — {currentSymbol}
                </label>
                <select
                    className="select-brutal"
                    value={selectedSymbol || currentSymbol}
                    onChange={(e) => setSelectedSymbol(e.target.value === currentSymbol ? '' : e.target.value)}
                    disabled={loading}
                >
                    {SUPPORTED_SYMBOLS.map((s) => (
                        <option key={s} value={s}>{s}</option>
                    ))}
                </select>
            </div>

            {/* Spread + Requote */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                <div>
                    <label className="metric-label" style={{ display: 'block', marginBottom: '4px', opacity: 1, color: 'rgba(0,0,0,0.6)' }}>
                        SPREAD BPS
                    </label>
                    <input
                        type="number"
                        step="0.5"
                        min="1"
                        className="input-brutal"
                        placeholder={currentSpreadBps.toString()}
                        value={spreadBps}
                        onChange={(e) => setSpreadBps(e.target.value)}
                        disabled={loading}
                    />
                </div>
                <div>
                    <label className="metric-label" style={{ display: 'block', marginBottom: '4px', opacity: 1, color: 'rgba(0,0,0,0.6)' }}>
                        REQUOTE BPS
                    </label>
                    <input
                        type="number"
                        step="1"
                        min="1"
                        className="input-brutal"
                        placeholder={currentRequoteBps.toString()}
                        value={requoteBps}
                        onChange={(e) => setRequoteBps(e.target.value)}
                        disabled={loading}
                    />
                </div>
            </div>

            {/* Bid / Ask Notional */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '16px' }}>
                <div>
                    <label className="metric-label" style={{ display: 'block', marginBottom: '4px', opacity: 1, color: 'rgba(0,0,0,0.6)' }}>
                        BID $
                    </label>
                    <input
                        type="number"
                        step="50"
                        min="10"
                        className="input-brutal"
                        placeholder={currentBidNotional.toString()}
                        value={bidNotional}
                        onChange={(e) => setBidNotional(e.target.value)}
                        disabled={loading}
                    />
                </div>
                <div>
                    <label className="metric-label" style={{ display: 'block', marginBottom: '4px', opacity: 1, color: 'rgba(0,0,0,0.6)' }}>
                        ASK $
                    </label>
                    <input
                        type="number"
                        step="50"
                        min="10"
                        className="input-brutal"
                        placeholder={currentAskNotional.toString()}
                        value={askNotional}
                        onChange={(e) => setAskNotional(e.target.value)}
                        disabled={loading}
                    />
                </div>
            </div>

            {/* Apply */}
            <button
                onClick={handleApplyConfig}
                disabled={loading}
                className="btn btn-apply"
                style={{ marginBottom: '12px' }}
            >
                {loading && (selectedSymbol && selectedSymbol !== currentSymbol) ? (
                    <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                        <span className="spinner" /> SWITCHING...
                    </span>
                ) : (
                    'APPLY CONFIG'
                )}
            </button>

            <hr className="divider divider-strong" style={{ borderColor: 'rgba(0,0,0,0.2)' }} />

            {/* Start / Stop */}
            <div style={{ display: 'flex', gap: '10px', marginBottom: '12px' }}>
                <button
                    id="btn-start"
                    onClick={handleStart}
                    disabled={isRunning || loading}
                    className="btn btn-start"
                    style={{ flex: 1 }}
                >
                    {loading && !isRunning ? <span className="spinner" /> : null}
                    {' '}START
                </button>
                <button
                    id="btn-stop"
                    onClick={handleStop}
                    disabled={isStopped || loading}
                    className="btn btn-stop"
                    style={{ flex: 1 }}
                >
                    {loading && isRunning ? <span className="spinner" /> : null}
                    {' '}STOP
                </button>
            </div>

            {/* Message */}
            {message && (
                <div style={{
                    padding: '8px 12px',
                    border: '2px solid rgba(0,0,0,0.3)',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                    background: message.startsWith('ERROR') ? 'rgba(231,76,60,0.2)' : 'rgba(0,0,0,0.1)',
                    textAlign: 'center',
                }}>
                    {message}
                </div>
            )}

            {/* Spacer to push version to bottom */}
            <div style={{ flex: 1 }} />
            <div style={{ fontSize: '0.6rem', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', opacity: 0.35, marginTop: '16px' }}>
                LOCAL ONLY — NOT FOR PRODUCTION
            </div>
        </div>
    );
}
