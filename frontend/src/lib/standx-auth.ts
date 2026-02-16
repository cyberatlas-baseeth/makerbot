/**
 * StandX Authentication Module
 *
 * Implements the full StandX Perps auth flow (per docs):
 * 1. Generate temporary ed25519 key pair (for request body signing)
 * 2. POST /v1/offchain/prepare-signin → get signedData JWT
 * 3. Parse signedData → extract SIWE message
 * 4. Sign SIWE message with wallet (via ethers.js BrowserProvider)
 * 5. POST /v1/offchain/login → get access token
 *
 * Uses ethers.js for wallet signing to match StandX's reference implementation.
 */

import { ed25519 } from '@noble/curves/ed25519.js';
import { base58 } from '@scure/base';
import { BrowserProvider } from 'ethers';

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

/**
 * Construct an EIP-4361 (SIWE) message from individual fields.
 * The format MUST match the ABNF specification exactly.
 *
 * Template:
 *   {domain} wants you to sign in with your Ethereum account:
 *   {address}
 *
 *   {statement}
 *
 *   URI: {uri}
 *   Version: {version}
 *   Chain ID: {chainId}
 *   Nonce: {nonce}
 *   Issued At: {issuedAt}
 *   Request ID: {requestId}
 */
function constructSiweMessage(payload: SignedData): string {
    const lines: string[] = [
        `${payload.domain} wants you to sign in with your Ethereum account:`,
        payload.address,
        '',                         // blank line separator
        payload.statement,
        '',                         // blank line separator
        `URI: ${payload.uri}`,
        `Version: ${payload.version}`,
        `Chain ID: ${payload.chainId}`,
        `Nonce: ${payload.nonce}`,
        `Issued At: ${payload.issuedAt}`,
    ];

    if (payload.requestId) {
        lines.push(`Request ID: ${payload.requestId}`);
    }

    return lines.join('\n');
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
     * Full authentication flow using ethers.js BrowserProvider for signing.
     * This matches StandX's reference EVM implementation exactly.
     */
    async authenticate(
        chain: Chain,
        walletAddress: string,
    ): Promise<LoginResponse> {
        if (!window.ethereum) {
            throw new Error('MetaMask not available');
        }

        // Step 1: Get signedData from StandX
        const signedDataJwt = await this.prepareSignIn(chain, walletAddress);

        // Step 2: Parse JWT to get the SIWE fields
        const payload = parseJwt<SignedData>(signedDataJwt);
        console.log('[StandX Auth] JWT payload fields:', {
            domain: payload.domain,
            address: payload.address,
            statement: payload.statement,
            uri: payload.uri,
            version: payload.version,
            chainId: payload.chainId,
            nonce: payload.nonce,
            issuedAt: payload.issuedAt,
            requestId: payload.requestId,
            hasMessageField: !!payload.message,
        });

        // Step 3: Build the SIWE message
        // If the JWT already contains a pre-constructed `message` field, use it.
        // Otherwise, construct it from the individual fields per EIP-4361.
        const siweMessage = payload.message || constructSiweMessage(payload);
        console.log('[StandX Auth] SIWE message to sign:\n', siweMessage);

        // Step 4: Sign with ethers.js BrowserProvider
        const provider = new BrowserProvider(window.ethereum);
        const signer = await provider.getSigner();
        const signature = await signer.signMessage(siweMessage);

        // Step 5: Login with signature
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

        if (!res.ok) {
            const errText = await res.text();
            throw new Error(`StandX prepare-signin failed: ${errText}`);
        }

        const data = await res.json();
        if (!data.success) {
            throw new Error(`StandX prepare-signin rejected: ${JSON.stringify(data)}`);
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
     */
    signRequest(payload: string): RequestSignatureHeaders {
        const version = 'v1';
        const requestId = crypto.randomUUID();
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

    getEd25519PrivateKeyHex(): string {
        return Array.from(this.ed25519PrivateKey)
            .map((b) => b.toString(16).padStart(2, '0'))
            .join('');
    }

    getRequestId(): string {
        return this.requestId;
    }
}
