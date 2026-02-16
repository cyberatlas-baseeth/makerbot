/**
 * Login page with MetaMask wallet connection.
 *
 * Flow:
 * 1. User clicks "Connect Wallet" → MetaMask pops up
 * 2. After connecting, clicks "Sign In to StandX"
 * 3. StandX prepareSignIn → MetaMask signs message → StandX login
 * 4. JWT token + ed25519 keys sent to backend → engine starts
 * 5. Redirect to dashboard
 */

import { useState } from 'react';
import { useWallet } from '../hooks/useWallet';
import { StandXAuth } from '../lib/standx-auth';

interface LoginPageProps {
    onAuthenticated: (token: string, address: string, ed25519PrivateKeyHex: string) => void;
}

export default function LoginPage({ onAuthenticated }: LoginPageProps) {
    const { address, isConnecting, error: walletError, hasMetaMask, connect } = useWallet();
    const [isAuthenticating, setIsAuthenticating] = useState(false);
    const [authError, setAuthError] = useState<string | null>(null);

    const handleStandXLogin = async () => {
        if (!address) return;

        setIsAuthenticating(true);
        setAuthError(null);

        try {
            // Create StandX auth instance (generates ed25519 key pair)
            const auth = new StandXAuth();

            // Authenticate: prepare-signin → ethers.js signs via MetaMask → login
            const loginResponse = await auth.authenticate('bsc', address);

            // Send token + ed25519 key to backend
            const res = await fetch('http://localhost:8000/api/auth/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: loginResponse.token,
                    address: loginResponse.address,
                    chain: loginResponse.chain,
                    ed25519_private_key_hex: auth.getEd25519PrivateKeyHex(),
                    request_id: auth.getRequestId(),
                }),
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Backend rejected authentication');
            }

            onAuthenticated(loginResponse.token, loginResponse.address, auth.getEd25519PrivateKeyHex());
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Authentication failed';
            setAuthError(message);
        } finally {
            setIsAuthenticating(false);
        }
    };

    return (
        <div className="min-h-screen bg-bg-primary flex items-center justify-center">
            <div className="w-full max-w-md mx-4">
                {/* Logo + Title */}
                <div className="text-center mb-8">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent to-[#8b5cf6] flex items-center justify-center mx-auto mb-4 shadow-lg shadow-accent/20">
                        <span className="text-white font-bold text-2xl">SX</span>
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight">StandX Market Maker</h1>
                    <p className="text-text-muted text-sm mt-1">Connect your wallet to start the bot</p>
                </div>

                {/* Login Card */}
                <div className="glass-card p-6 rounded-2xl">
                    {/* Step 1: Connect Wallet */}
                    <div className="mb-6">
                        <div className="flex items-center gap-2 mb-3">
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${address ? 'bg-green-500/20 text-green-400' : 'bg-accent/20 text-accent'
                                }`}>
                                {address ? '✓' : '1'}
                            </div>
                            <span className="text-sm font-medium">Connect Wallet</span>
                        </div>

                        {!hasMetaMask ? (
                            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-sm">
                                <p className="text-red-400 font-medium mb-1">MetaMask not detected</p>
                                <p className="text-text-muted text-xs">
                                    Install{' '}
                                    <a
                                        href="https://metamask.io/download/"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-accent underline"
                                    >
                                        MetaMask
                                    </a>{' '}
                                    to continue.
                                </p>
                            </div>
                        ) : address ? (
                            <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-3 flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center">
                                    <span className="text-white text-xs">🦊</span>
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-xs text-text-muted">Connected</p>
                                    <p className="text-sm font-mono truncate">{address}</p>
                                </div>
                            </div>
                        ) : (
                            <button
                                onClick={connect}
                                disabled={isConnecting}
                                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-400 hover:to-orange-500 text-white font-medium text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                            >
                                {isConnecting ? (
                                    <>
                                        <span className="animate-spin">⏳</span>
                                        Connecting...
                                    </>
                                ) : (
                                    <>
                                        <span>🦊</span>
                                        Connect MetaMask
                                    </>
                                )}
                            </button>
                        )}
                    </div>

                    {/* Divider */}
                    <div className="border-t border-border my-4" />

                    {/* Step 2: Sign In to StandX */}
                    <div>
                        <div className="flex items-center gap-2 mb-3">
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${!address ? 'bg-border text-text-muted' : 'bg-accent/20 text-accent'
                                }`}>
                                2
                            </div>
                            <span className="text-sm font-medium">Sign In to StandX</span>
                        </div>

                        <p className="text-text-muted text-xs mb-3">
                            StandX will ask you to sign a message in MetaMask to verify your identity. No gas fees.
                        </p>

                        <button
                            onClick={handleStandXLogin}
                            disabled={!address || isAuthenticating}
                            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-accent to-[#8b5cf6] hover:brightness-110 text-white font-medium text-sm transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {isAuthenticating ? (
                                <>
                                    <span className="animate-spin">⏳</span>
                                    Authenticating...
                                </>
                            ) : (
                                <>Sign In to StandX &amp; Start Bot</>
                            )}
                        </button>
                    </div>

                    {/* Errors */}
                    {(walletError || authError) && (
                        <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-xl p-3">
                            <p className="text-red-400 text-xs">{walletError || authError}</p>
                        </div>
                    )}
                </div>

                {/* Security Note */}
                <p className="text-text-muted text-xs text-center mt-6">
                    This bot runs locally. Your private key never leaves MetaMask.
                </p>
            </div>
        </div>
    );
}
