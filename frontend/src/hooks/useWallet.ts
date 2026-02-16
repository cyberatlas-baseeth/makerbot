/**
 * MetaMask wallet connection hook.
 *
 * Handles:
 * - Connecting to MetaMask (window.ethereum)
 * - Getting wallet address
 * - Signing messages via personal_sign
 * - Detecting account/chain changes
 */

import { useState, useCallback, useEffect } from 'react';

// Extend window for MetaMask
declare global {
    interface Window {
        ethereum?: {
            isMetaMask?: boolean;
            request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
            on: (event: string, handler: (...args: unknown[]) => void) => void;
            removeListener: (event: string, handler: (...args: unknown[]) => void) => void;
        };
    }
}

interface WalletState {
    address: string | null;
    isConnecting: boolean;
    error: string | null;
}

export function useWallet() {
    const [state, setState] = useState<WalletState>({
        address: null,
        isConnecting: false,
        error: null,
    });

    const hasMetaMask = typeof window !== 'undefined' && !!window.ethereum?.isMetaMask;

    const connect = useCallback(async () => {
        if (!window.ethereum) {
            setState((s) => ({ ...s, error: 'MetaMask not detected. Please install MetaMask.' }));
            return null;
        }

        setState((s) => ({ ...s, isConnecting: true, error: null }));

        try {
            const accounts = (await window.ethereum.request({
                method: 'eth_requestAccounts',
            })) as string[];

            if (accounts.length === 0) {
                throw new Error('No accounts returned from MetaMask.');
            }

            const address = accounts[0];
            setState({ address, isConnecting: false, error: null });
            return address;
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to connect wallet';
            setState({ address: null, isConnecting: false, error: message });
            return null;
        }
    }, []);

    const signMessage = useCallback(
        async (message: string): Promise<string> => {
            if (!window.ethereum || !state.address) {
                throw new Error('Wallet not connected');
            }

            const signature = (await window.ethereum.request({
                method: 'personal_sign',
                params: [message, state.address],
            })) as string;

            return signature;
        },
        [state.address],
    );

    const disconnect = useCallback(() => {
        setState({ address: null, isConnecting: false, error: null });
    }, []);

    // Listen for account changes
    useEffect(() => {
        if (!window.ethereum) return;

        const handleAccountsChanged = (accounts: unknown) => {
            const accs = accounts as string[];
            if (accs.length === 0) {
                setState({ address: null, isConnecting: false, error: null });
            } else {
                setState({ address: accs[0], isConnecting: false, error: null });
            }
        };

        window.ethereum.on('accountsChanged', handleAccountsChanged);
        return () => {
            window.ethereum?.removeListener('accountsChanged', handleAccountsChanged);
        };
    }, []);

    return {
        address: state.address,
        isConnecting: state.isConnecting,
        error: state.error,
        hasMetaMask,
        connect,
        signMessage,
        disconnect,
    };
}
