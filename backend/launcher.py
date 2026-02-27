"""
Launcher GUI — tkinter popup for StandX credentials.

Shows a small window with JWT token, Ed25519 key, and wallet address fields.
If .env already exists, pre-fills the fields.
On "Start Bot" click: saves to .env, starts uvicorn, opens browser.
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


def get_app_dir() -> Path:
    """Return the directory where the exe (or script) lives."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def get_env_path() -> Path:
    return get_app_dir() / ".env"


def read_env() -> dict[str, str]:
    """Read existing .env file into a dict."""
    env_path = get_env_path()
    values: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip()
    return values


def write_env(jwt_token: str, private_key: str, wallet: str, chain: str) -> None:
    """Write credentials to .env alongside the exe."""
    env_path = get_env_path()

    # Read existing values to preserve non-credential settings
    existing = read_env()
    existing["STANDX_JWT_TOKEN"] = jwt_token
    existing["STANDX_ED25519_PRIVATE_KEY"] = private_key
    existing["STANDX_WALLET_ADDRESS"] = wallet
    existing["STANDX_CHAIN"] = chain

    # Ensure defaults exist
    defaults = {
        "STANDX_API_BASE": "https://perps.standx.com",
        "STANDX_WS_URL": "wss://perps.standx.com/ws-stream/v1",
        "SYMBOL": "BTC-USD",
        "SPREAD_BPS": "50.0",
        "BID_NOTIONAL": "30.0",
        "ASK_NOTIONAL": "30.0",
        "REFRESH_INTERVAL": "1.0",
        "REQUOTE_THRESHOLD_BPS": "25.0",
        "PROXIMITY_GUARD_BPS": "1.0",
        "MAX_NOTIONAL": "10000.0",
        "MAX_CONSECUTIVE_FAILURES": "5",
        "STALE_ORDER_SECONDS": "30",
        "MAX_SPREAD_DEVIATION_BPS": "200",
        "TP_USD": "0.0",
        "SL_USD": "0.0",
        "UPTIME_TARGET_MINUTES": "30",
    }
    for k, v in defaults.items():
        existing.setdefault(k, v)

    lines = [f"{k}={v}" for k, v in existing.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def start_server() -> None:
    """Start uvicorn programmatically."""
    import webbrowser
    import uvicorn

    # Set env file path for pydantic-settings
    os.environ["ENV_FILE"] = str(get_env_path())

    # Brief delay then open browser
    def open_browser():
        time.sleep(3)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


class LauncherApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("MakerBot — StandX Market Maker")
        self.root.geometry("560x500")
        self.root.resizable(False, False)
        self.root.configure(bg="#0f172a")

        # Try to center on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 560) // 2
        y = (self.root.winfo_screenheight() - 500) // 2
        self.root.geometry(f"560x500+{x}+{y}")

        self._build_ui()
        self._load_existing()

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TFrame", background="#0f172a")
        style.configure("Dark.TLabel", background="#0f172a", foreground="#e2e8f0",
                         font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#0f172a", foreground="#38bdf8",
                         font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", background="#0f172a", foreground="#64748b",
                         font=("Segoe UI", 9))
        style.configure("Start.TButton", font=("Segoe UI", 12, "bold"),
                         padding=(20, 12))

        main = ttk.Frame(self.root, style="Dark.TFrame", padding=30)
        main.pack(fill="both", expand=True)

        # Title
        ttk.Label(main, text="🤖 MakerBot", style="Title.TLabel").pack(pady=(0, 2))
        ttk.Label(main, text="StandX Perps Market Maker", style="Sub.TLabel").pack(pady=(0, 20))

        # Fields
        fields_frame = ttk.Frame(main, style="Dark.TFrame")
        fields_frame.pack(fill="x")

        self.jwt_var = tk.StringVar()
        self.key_var = tk.StringVar()
        self.wallet_var = tk.StringVar()
        self.chain_var = tk.StringVar(value="bsc")

        self._add_field(fields_frame, "JWT Token", self.jwt_var, 0, show="•")
        self._add_field(fields_frame, "Ed25519 Private Key", self.key_var, 1, show="•")
        self._add_field(fields_frame, "Wallet Address (0x...)", self.wallet_var, 2)
        self._add_field(fields_frame, "Chain", self.chain_var, 3)

        # Start button
        btn_frame = ttk.Frame(main, style="Dark.TFrame")
        btn_frame.pack(fill="x", pady=(20, 0))

        self.start_btn = tk.Button(
            btn_frame,
            text="🚀  Start Bot",
            font=("Segoe UI", 14, "bold"),
            bg="#10b981",
            fg="white",
            activebackground="#059669",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self._on_start,
            pady=14,
        )
        self.start_btn.pack(fill="x", ipady=6)

    def _add_field(self, parent: ttk.Frame, label: str, var: tk.StringVar,
                   row: int, show: str = "") -> None:
        ttk.Label(parent, text=label, style="Dark.TLabel").grid(
            row=row * 2, column=0, sticky="w", pady=(8, 2))
        entry = tk.Entry(
            parent,
            textvariable=var,
            font=("Consolas", 10),
            bg="#1e293b",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            relief="flat",
            highlightthickness=1,
            highlightcolor="#38bdf8",
            highlightbackground="#334155",
        )
        if show:
            entry.configure(show=show)
        entry.grid(row=row * 2 + 1, column=0, sticky="ew", ipady=6)
        parent.columnconfigure(0, weight=1)

    def _load_existing(self) -> None:
        existing = read_env()
        if "STANDX_JWT_TOKEN" in existing:
            self.jwt_var.set(existing["STANDX_JWT_TOKEN"])
        if "STANDX_ED25519_PRIVATE_KEY" in existing:
            self.key_var.set(existing["STANDX_ED25519_PRIVATE_KEY"])
        if "STANDX_WALLET_ADDRESS" in existing:
            self.wallet_var.set(existing["STANDX_WALLET_ADDRESS"])
        if "STANDX_CHAIN" in existing:
            self.chain_var.set(existing["STANDX_CHAIN"])

    def _on_start(self) -> None:
        jwt = self.jwt_var.get().strip()
        key = self.key_var.get().strip()
        wallet = self.wallet_var.get().strip()
        chain = self.chain_var.get().strip() or "bsc"

        if not jwt or not key or not wallet:
            messagebox.showwarning(
                "Missing Credentials",
                "Please fill in JWT Token, Private Key, and Wallet Address.",
            )
            return

        # Save to .env
        write_env(jwt, key, wallet, chain)

        # Close the GUI
        self.root.destroy()

        # Start the server (blocking)
        print("\n" + "=" * 50)
        print("  MakerBot starting on http://localhost:8000")
        print("  Press Ctrl+C to stop")
        print("=" * 50 + "\n")

        start_server()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = LauncherApp()
    app.run()


if __name__ == "__main__":
    main()
