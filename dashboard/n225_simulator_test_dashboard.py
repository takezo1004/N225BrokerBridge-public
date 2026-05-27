"""
N225 Simulator Test Dashboard
==============================
N225BrokerBridge の --simulator モードを起動し、Webhook ペイロード 7 種を
ボタン 1 つで発火して動作確認できる Tkinter ダッシュボード。

ユースケース:
- 配布物の動作デモ (購読者が clone 直後に動かせる)
- 開発者の回帰テスト
- ブログ第 2 話の素材撮影

仕組み:
- [Start Bridge] でシミュレータ設定 (passphrase=abcdefg + TestStrategy 登録) を
  %LOCALAPPDATA%\\N225BrokerBridge\\*.simulator.json に書き出して N225BrokerBridge.UI.exe --simulator を起動
- 7 ボタンで docs/webhook_test/payloads/*.json を POST
- レスポンスは「レスポンスログ」に表示
- Bridge の log file を 1 秒間隔で tail して「Bridge ログ」に表示

依存: Python 3.10+ 標準ライブラリのみ (tkinter / urllib / subprocess / json / threading)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from tkinter import scrolledtext, ttk


# ─── 定数 ─────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
WEBHOOK_URL = "http://localhost:8000/webhook/"


def _resolve_bridge_exe() -> Path:
    """Bridge exe を開発環境と配布環境の両方で見つける。
    開発環境 (リポ直下): N225BrokerBridge/src/N225BrokerBridge.UI/bin/Debug/net8.0-windows/N225BrokerBridge.UI.exe
    配布環境 (public/dashboard): ../bridge/src/N225BrokerBridge.UI/bin/Debug/net8.0-windows/N225BrokerBridge.UI.exe
    """
    candidates = [
        SCRIPT_DIR / "N225BrokerBridge" / "src" / "N225BrokerBridge.UI" / "bin" / "Debug"
            / "net8.0-windows" / "N225BrokerBridge.UI.exe",
        SCRIPT_DIR.parent / "bridge" / "src" / "N225BrokerBridge.UI" / "bin" / "Debug"
            / "net8.0-windows" / "N225BrokerBridge.UI.exe",
        SCRIPT_DIR / "N225BrokerBridge" / "src" / "N225BrokerBridge.UI" / "bin" / "Release"
            / "net8.0-windows" / "N225BrokerBridge.UI.exe",
        SCRIPT_DIR.parent / "bridge" / "src" / "N225BrokerBridge.UI" / "bin" / "Release"
            / "net8.0-windows" / "N225BrokerBridge.UI.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]  # 見つからなくても最初の候補を返す (エラー文言で使う)


def _resolve_payload_dir() -> Path:
    """ペイロードフォルダを開発環境と配布環境の両方で見つける。
    開発環境 (リポ直下): docs/webhook_test/payloads/
    配布環境 (public/dashboard): webhook_test/payloads/  (sync が docs/webhook_test → webhook_test に展開)
    """
    candidates = [
        SCRIPT_DIR / "docs" / "webhook_test" / "payloads",
        SCRIPT_DIR / "webhook_test" / "payloads",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


DEFAULT_BRIDGE_EXE = _resolve_bridge_exe()
DEFAULT_PAYLOAD_DIR = _resolve_payload_dir()

LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\takao2\AppData\Local"))
SIMULATOR_DIR = LOCAL_APP_DATA / "N225BrokerBridge"
SIMULATOR_SETTINGS = SIMULATOR_DIR / "appsettings.Local.simulator.json"
SIMULATOR_STRATEGIES = SIMULATOR_DIR / "strategies.simulator.json"
BRIDGE_LOG_DIR = SIMULATOR_DIR / "logs"

# Bridge 起動時に投入する設定
SIMULATOR_PASSPHRASE = "abcdefg"   # payloads と整合
SIMULATOR_PORT = 8000              # appsettings.json 既定値と整合
TEST_STRATEGY_NAME = "TestStrategy"
TEST_STRATEGY_INTERVAL = 5

# 7 ペイロード定義 (順序 = 画面上の並び)
PAYLOADS = [
    ("1. 認証失敗",        "01_auth_failed.json",          "Authenticated_Failed"),
    ("2. Bad JSON",        "02_bad_json.txt",              "Bad Request"),
    ("3. 新規買い",        "03_new_buy.json",              "NewOrderDispatched_"),
    ("4. 返済",            "04_exit_long.json",            "ExitOrderDispatched_"),
    ("5. ドテン",          "05_doten_short_to_long.json",  "DotenDispatched_"),
    ("6. flat→flat",       "06_ignored_flat_to_flat.json", "Ignored_"),
    ("7. 戦略未登録",      "07_not_registered.json",       "Ignored_"),
]


# ─── シミュレータ設定書き出し ─────────────────────────────
def write_simulator_settings() -> tuple[Path, Path]:
    """Bridge 起動前に、--simulator が読む設定ファイル 2 つを生成する。
    既存ファイルがあれば上書きする (テスト都度クリーンな状態にする)。
    """
    SIMULATOR_DIR.mkdir(parents=True, exist_ok=True)

    # 1) appsettings.Local.simulator.json
    # 平文 passphrase で OK (LocalSettingsStore は enc: プレフィックスがない値も読める)
    settings = {
        "Webhook": {
            "Port": SIMULATOR_PORT,
            "Passphrase": SIMULATOR_PASSPHRASE,
        },
        "Behavior": {
            "RequireConfirmBeforeOrder": True,
        },
    }
    SIMULATOR_SETTINGS.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 2) strategies.simulator.json
    strategies = [
        {
            "alertName": TEST_STRATEGY_NAME,
            "interval": TEST_STRATEGY_INTERVAL,
            "isEnabled": True,
            "description": "Simulator test dashboard が自動登録した戦略",
        }
    ]
    SIMULATOR_STRATEGIES.write_text(
        json.dumps(strategies, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return SIMULATOR_SETTINGS, SIMULATOR_STRATEGIES


# ─── ダッシュボード本体 ─────────────────────────────────
class SimulatorTestDashboard:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("N225 Simulator Test Dashboard")
        self.root.geometry("900x800")

        self.bridge_exe = DEFAULT_BRIDGE_EXE
        self.payload_dir = DEFAULT_PAYLOAD_DIR
        self.bridge_proc: subprocess.Popen | None = None
        self.log_tail_thread: threading.Thread | None = None
        self.log_tail_stop = threading.Event()
        self.current_log_file: Path | None = None
        self.log_file_pos = 0

        self._build_ui()
        self._refresh_bridge_status()

    # ── UI ────────────────────────────────────────────
    def _build_ui(self):
        # ── Bridge プロセス制御 ──
        ctrl = ttk.LabelFrame(self.root, text="Bridge プロセス", padding=8)
        ctrl.pack(fill=tk.X, padx=8, pady=4)

        self.status_var = tk.StringVar(value="Stopped")
        ttk.Label(ctrl, text="状態:").grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(
            ctrl, textvariable=self.status_var, foreground="gray", font=("Consolas", 10, "bold")
        )
        self.status_label.grid(row=0, column=1, sticky="w", padx=8)

        self.start_btn = ttk.Button(ctrl, text="Start Bridge (--simulator)", command=self.on_start_bridge)
        self.start_btn.grid(row=0, column=2, padx=4)
        self.stop_btn = ttk.Button(ctrl, text="Stop Bridge", command=self.on_stop_bridge, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=3, padx=4)

        ttk.Label(ctrl, text=f"URL: {WEBHOOK_URL}").grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 0))

        # ── Webhook 発火ボタン (3 列 x 3 行) ──
        webhook = ttk.LabelFrame(self.root, text="Webhook ペイロード発火", padding=8)
        webhook.pack(fill=tk.X, padx=8, pady=4)

        self.payload_buttons: list[ttk.Button] = []
        for i, (label, filename, _expect) in enumerate(PAYLOADS):
            row = i // 3
            col = i % 3
            btn = ttk.Button(webhook, text=label, width=25, command=lambda idx=i: self.on_fire_payload(idx))
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            btn.config(state=tk.DISABLED)
            self.payload_buttons.append(btn)

        # 3 列均等
        for col in range(3):
            webhook.grid_columnconfigure(col, weight=1)

        # ── レスポンスログ ──
        resp_frame = ttk.LabelFrame(self.root, text="レスポンスログ", padding=8)
        resp_frame.pack(fill=tk.BOTH, expand=False, padx=8, pady=4)
        self.response_log = scrolledtext.ScrolledText(
            resp_frame, height=10, font=("Consolas", 9), wrap=tk.NONE
        )
        self.response_log.pack(fill=tk.BOTH, expand=True)
        self.response_log.tag_config("pass", foreground="green")
        self.response_log.tag_config("fail", foreground="red")
        self.response_log.tag_config("info", foreground="black")

        # ── Bridge ログ tail ──
        bridge_frame = ttk.LabelFrame(self.root, text="Bridge ログ (最新分のみ tail)", padding=8)
        bridge_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self.bridge_log = scrolledtext.ScrolledText(
            bridge_frame, height=16, font=("Consolas", 8), wrap=tk.NONE, background="#1e1e1e", foreground="#d4d4d4"
        )
        self.bridge_log.pack(fill=tk.BOTH, expand=True)

        # ── 終了時のクリーンアップ ──
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ── 状態反映 ───────────────────────────────────────
    def _refresh_bridge_status(self):
        running = self.bridge_proc is not None and self.bridge_proc.poll() is None
        if running:
            self.status_var.set(f"Running (PID {self.bridge_proc.pid})  port {SIMULATOR_PORT}")
            self.status_label.config(foreground="green")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            for btn in self.payload_buttons:
                btn.config(state=tk.NORMAL)
        else:
            self.status_var.set("Stopped")
            self.status_label.config(foreground="gray")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            for btn in self.payload_buttons:
                btn.config(state=tk.DISABLED)
            if self.bridge_proc is not None and self.bridge_proc.poll() is not None:
                # プロセスが死んだ場合は参照クリア
                self.bridge_proc = None
        # 1 秒ごとに再評価
        self.root.after(1000, self._refresh_bridge_status)

    # ── Bridge 起動/停止 ──────────────────────────────────
    def on_start_bridge(self):
        if self.bridge_proc and self.bridge_proc.poll() is None:
            self._log_response("info", "Bridge は既に起動しています")
            return

        if not self.bridge_exe.exists():
            self._log_response("fail", f"Bridge exe が見つかりません: {self.bridge_exe}")
            return

        # 1) シミュレータ設定を書き出す (毎回上書き = テストの再現性確保)
        try:
            sp, sg = write_simulator_settings()
            self._log_response("info", f"設定書き出し OK: {sp.name} / {sg.name}")
        except Exception as e:
            self._log_response("fail", f"設定書き出し失敗: {e}")
            return

        # 2) Bridge を起動
        try:
            self.bridge_proc = subprocess.Popen(
                [str(self.bridge_exe), "--simulator"],
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
            )
            self._log_response("info", f"Bridge 起動 (PID {self.bridge_proc.pid})")
        except Exception as e:
            self._log_response("fail", f"Bridge 起動失敗: {e}")
            return

        # 3) ログ tail スレッド起動
        self.log_tail_stop.clear()
        self.log_tail_thread = threading.Thread(target=self._log_tail_loop, daemon=True)
        self.log_tail_thread.start()

    def on_stop_bridge(self):
        if self.bridge_proc and self.bridge_proc.poll() is None:
            try:
                self.bridge_proc.terminate()
                self.bridge_proc.wait(timeout=5)
                self._log_response("info", "Bridge 停止")
            except subprocess.TimeoutExpired:
                self.bridge_proc.kill()
                self._log_response("info", "Bridge 強制停止")
            except Exception as e:
                self._log_response("fail", f"Bridge 停止失敗: {e}")
        self.log_tail_stop.set()
        self.bridge_proc = None

    # ── ペイロード送信 ─────────────────────────────────
    def on_fire_payload(self, index: int):
        label, filename, expect = PAYLOADS[index]
        path = self.payload_dir / filename
        if not path.exists():
            self._log_response("fail", f"ペイロード見つかりません: {path}")
            return
        body = path.read_bytes()

        # ボタン連打防止
        self.payload_buttons[index].config(state=tk.DISABLED)
        threading.Thread(target=self._send_payload_worker, args=(label, body, expect, index), daemon=True).start()

    def _send_payload_worker(self, label: str, body: bytes, expect: str, index: int):
        try:
            req = urllib.request.Request(
                WEBHOOK_URL,
                data=body,
                method="POST",
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
                text = resp.read().decode("utf-8", errors="replace").strip()
        except urllib.error.HTTPError as e:
            status = e.code
            try:
                text = e.read().decode("utf-8", errors="replace").strip()
            except Exception:
                text = str(e)
        except Exception as e:
            self.root.after(0, self._log_response, "fail", f"{label} → 接続エラー: {e}")
            self.root.after(0, self._reenable_button, index)
            return

        ok = expect in text
        tag = "pass" if ok else "fail"
        mark = "PASS" if ok else "FAIL"
        self.root.after(0, self._log_response, tag, f"[{mark}] {label} → HTTP {status}  body={text}")
        self.root.after(0, self._reenable_button, index)

    def _reenable_button(self, index: int):
        running = self.bridge_proc is not None and self.bridge_proc.poll() is None
        if running:
            self.payload_buttons[index].config(state=tk.NORMAL)

    # ── ログ tail ────────────────────────────────────
    def _log_tail_loop(self):
        # 起動直後はログがまだ無いので少し待つ
        time.sleep(1.0)
        while not self.log_tail_stop.is_set():
            try:
                log_file = self._find_latest_log_file()
                if log_file is None:
                    time.sleep(1.0)
                    continue
                if log_file != self.current_log_file:
                    # 新しい日のログに切り替わったら最初から
                    self.current_log_file = log_file
                    self.log_file_pos = 0
                with open(log_file, "rb") as f:
                    f.seek(self.log_file_pos)
                    new_bytes = f.read()
                    self.log_file_pos = f.tell()
                if new_bytes:
                    text = new_bytes.decode("utf-8", errors="replace")
                    # MainThread に投げる
                    self.root.after(0, self._append_bridge_log, text)
            except Exception:
                pass
            time.sleep(1.0)

    def _find_latest_log_file(self) -> Path | None:
        if not BRIDGE_LOG_DIR.exists():
            return None
        candidates = sorted(BRIDGE_LOG_DIR.glob("n225brokerbridge-*.log"), key=lambda p: p.stat().st_mtime)
        return candidates[-1] if candidates else None

    def _append_bridge_log(self, text: str):
        self.bridge_log.insert(tk.END, text)
        # 行数が増えすぎたら古い行を削る (上限 1000 行)
        line_count = int(self.bridge_log.index("end-1c").split(".")[0])
        if line_count > 1000:
            self.bridge_log.delete("1.0", f"{line_count - 1000}.0")
        self.bridge_log.see(tk.END)

    # ── レスポンスログ ─────────────────────────────────
    def _log_response(self, tag: str, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.response_log.insert(tk.END, f"[{ts}] {text}\n", tag)
        self.response_log.see(tk.END)

    # ── 終了 ───────────────────────────────────────────
    def on_close(self):
        if self.bridge_proc and self.bridge_proc.poll() is None:
            self.on_stop_bridge()
        self.log_tail_stop.set()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        from tkinter import font as tkfont
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Yu Gothic UI", size=9)
    except Exception:
        pass
    SimulatorTestDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
