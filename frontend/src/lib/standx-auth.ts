/**
 * StandX Authentication Module
 *
 * Implements the full StandX Perps auth flow:
 * 1. Generate temporary ed25519 key pair (for request body signing)
 * 2. POST /v1/offchain/prepare-signin → get signedData JWT
 * 3. Parse signedData → extract message to sign
 * 4. Sign message with MetaMask (EVM wallet)
 * 5. POST /v1/offchain/login → get access token
 *
 * The ed25519 key pair is stored in memory for signing subsequent
 * API request bodies per StandX's body signature flow.
 */

import { ed25519 } from '@noble/curves/ed25519.js';
import { base58 } from '@scure/base';

const STANDX_AUTH_BASE = 'https://api.standx.com';

export type Chain = 'bsc' | 'solana';

export interface SignedData {
    domain: string;
    uri: string;
    statement: string;
    version: string;
    chainId: number;
    nonce: string;
    address: string;
    requestId: string;
    issuedAt: string;
    message: string;
    exp: number;
    iat: number;
}

export interface LoginResponse {
    token: string;
    address: string;
    alias: string;
    chain: string;
    perpsAlpha: boolean;
}

export interface RequestSignatureHeaders {
    'x-request-sign-version': string;
    'x-request-id': string;
    'x-request-timestamp': string;
    'x-request-signature': string;
}

function parseJwt<T>(token: string): T {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64));
}

function generateUUID(): string {
    return crypto.randomUUID();
}

export class StandXAuth {
    private ed25519PrivateKey: Uint8Array;
    private ed25519PublicKey: Uint8Array;
    private requestId: string;

    constructor() {
        // Generate temporary ed25519 key pair for body signing
        const privateKey = ed25519.utils.randomSecretKey();
        this.ed25519PrivateKey = privateKey;
        this.ed25519PublicKey = ed25519.getPublicKey(privateKey);
        this.requestId = base58.encode(this.ed25519PublicKey);
    }

    /**
     * Full authentication flow:
     * 1. Prepare sign-in with StandX
     * 2. Get MetaMask to sign the message
     * 3. Submit signature to get JWT token
     */
    async authenticate(
        chain: Chain,
        walletAddress: string,
        signMessage: (msg: string) => Promise<string>,
    ): Promise<LoginResponse> {
        // Step 1: Get signedData from StandX
        const signedDataJwt = await this.prepareSignIn(chain, walletAddress);

        // Step 2: Parse JWT to get the message
        const payload = parseJwt<SignedData>(signedDataJwt);

        // Step 3: Sign with MetaMask
        const signature = await signMessage(payload.message);

        // Step 4: Login with signature
        return this.login(chain, signature, signedDataJwt);
    }

    private async prepareSignIn(chain: Chain, address: string): Promise<string> {
        const res = await fetch(
            `${STANDX_AUTH_BASE}/v1/offchain/prepare-signin?chain=${chain}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    address,
                    requestId: this.requestId,
                }),
            },
        );

        const data = await res.json();
        if (!data.success) {
            throw new Error('Failed to prepare sign-in with StandX');
        }
        return data.signedData;
    }

    private async login(
        chain: Chain,
        signature: string,
        signedData: string,
        expiresSeconds: number = 604800, // 7 days
    ): Promise<LoginResponse> {
        const res = await fetch(
            `${STANDX_AUTH_BASE}/v1/offchain/login?chain=${chain}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ signature, signedData, expiresSeconds }),
            },
        );

        if (!res.ok) {
            const errText = await res.text();
            throw new Error(`StandX login failed: ${errText}`);
        }

        return res.json();
    }

    /**
     * Sign a request body per StandX's body signature flow.
     * Returns headers to attach to the API request.
     */
    signRequest(payload: string): RequestSignatureHeaders {
        const version = 'v1';
        const requestId = generateUUID();
        const timestamp = Date.now();
        const message = `${version},${requestId},${timestamp},${payload}`;
        const messageBytes = new TextEncoder().encode(message);
        const signature = ed25519.sign(messageBytes, this.ed25519PrivateKey);

        return {
            'x-request-sign-version': version,
            'x-request-id': requestId,
            'x-request-timestamp': timestamp.toString(),
            'x-request-signature': btoa(String.fromCharCode(...signature)),
        };
    }

    /**
     * Get the ed25519 private key (hex) for backend use.
     */
    getEd25519PrivateKeyHex(): string {
        return Array.from(this.ed25519PrivateKey)
            .map((b) => b.toString(16).padStart(2, '0'))
            .join('');
    }

    /**
     * Get the requestId (base58-encoded ed25519 public key).
     */
    getRequestId(): string {
        return this.requestId;
    }
}
