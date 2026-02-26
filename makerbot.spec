# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for MakerBot.

Bundles:
  - launcher.py as entry point (tkinter GUI → uvicorn)
  - All backend app/ modules
  - Frontend dist/ as embedded static files
"""

import os

block_cipher = None

# Paths
backend_dir = os.path.dirname(os.path.abspath(SPEC))
backend_app = os.path.join(backend_dir, 'backend')
frontend_dist = os.path.join(backend_dir, 'frontend', 'dist')

a = Analysis(
    [os.path.join(backend_app, 'launcher.py')],
    pathex=[backend_app],
    binaries=[],
    datas=[
        # Embed frontend build
        (frontend_dist, 'frontend_dist'),
    ],
    hiddenimports=[
        'app',
        'app.main',
        'app.config',
        'app.logger',
        'app.auth',
        'app.auth.jwt_auth',
        'app.market_data',
        'app.market_data.orderbook',
        'app.market_data.ws_client',
        'app.trading',
        'app.trading.engine',
        'app.trading.quote',
        'app.uptime',
        'app.uptime.tracker',
        'app.api',
        'app.api.routes',
        'app.api.ws',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'httptools',
        'websockets',
        'httpx',
        'httpx._transports',
        'httpx._transports.default',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
        'structlog',
        'pydantic',
        'pydantic_settings',
        'nacl',
        'nacl.signing',
        'nacl.bindings',
        'nacl._sodium',
        'nacl.utils',
        'nacl.exceptions',
        'cffi',
        '_cffi_backend',
        'base58',
        'tenacity',
        'dotenv',
        'email.mime.text',
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.asymmetric',
        'cryptography.hazmat.primitives.asymmetric.ed25519',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',
        'cryptography.hazmat.bindings',
        'cryptography.hazmat.bindings._rust',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'pytest_asyncio'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='makerbot-v2.0.1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,     # Console stays open for logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
