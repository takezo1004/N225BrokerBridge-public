"""
N225BrokerBridge ダッシュボード B (本番運用専用)

3 カード横展開レイアウト。朝起動 → トレード本番 → 停止 の流れを
左から右に視覚的に表現する。

担当機能:
  1. kabu Station 接続ステータス (ヘッダーで LED 風表示、3 秒間隔ポーリング)
  2. TradingView デバッグモード起動 (launch_tradingview_debug_msix.ps1)
  3. 株式分析実行 (pwsh -NoExit 経由で claude を新コンソール対話起動 → /analyze 自動投入 / SHELL=pwsh で Claude Code 内 Bash ツールも PowerShell 構文として動作)
  4. 本番起動 (cloudflared → ブリッジ 連動)
  5. 停止 (ブリッジ → cloudflared 連動)

旧 n225_dashboard.py とは独立。互いに干渉しない。
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
import urllib.error
import urllib.request
from datetime import datetime
from tkinter import scrolledtext

# ─────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BRIDGE_EXE = os.path.join(
    BASE_DIR, "N225BrokerBridge", "src", "N225BrokerBridge.UI",
    "bin", "Debug", "net8.0-windows", "N225BrokerBridge.UI.exe"
)

TV_LAUNCH_PS1 = os.path.join(
    BASE_DIR, "N225SignalTrader", "scripts", "launch_tradingview_debug_msix.ps1"
)
PWSH_EXE = r"C:\Program Files\PowerShell\7\pwsh.exe"

CLOUDFLARED_EXE = "cloudflared"
CLOUDFLARED_TUNNEL_NAME = "n225-webhook"

KABU_HEALTH_URL = "http://localhost:18080/kabusapi/"
KABU_HEALTH_TIMEOUT_SEC = 1.5

VENV_PYTHON = os.path.join(BASE_DIR, "N225SignalTrader", ".venv", "Scripts", "python.exe")
PREVIEW_PY = os.path.join(BASE_DIR, "N225LLMAdvisor", "src", "preview_analysis.py")
ANALYSIS_DIR = os.path.join(BASE_DIR, "N225LLMAdvisor", "analyses")
TV_CDP_URL = "http://127.0.0.1:9222/json/version"
TV_CDP_TIMEOUT_SEC = 2.0

# Claude Code のネストセッションガード回避用に親プロセスから外す環境変数
CLAUDE_ENV_VARS_TO_STRIP = [
    "CLAUDECODE",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_EXECPATH",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING",
    "CLAUDE_CODE_ENABLE_TASKS",
    "CLAUDE_EFFORT",
    "AI_AGENT",
]

# 配色 (Tokyo Night 系)
BG          = "#1a1b26"      # 本背景 (より暗めに変更)
PANEL_BG    = "#24283b"      # カード背景
PANEL_BG_HI = "#2f344d"      # カードヘッダー
FG          = "#c0caf5"
FG_DIM      = "#737aa2"
ACCENT      = "#7aa2f7"      # 青
GREEN       = "#9ece6a"
YELLOW      = "#e0af68"
RED         = "#f7768e"
PURPLE      = "#bb9af7"

# ステータス LED
LED_ON  = GREEN
LED_OFF = "#3b4261"
LED_ERR = RED


class BrokerBridgeDashboard:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("N225BrokerBridge Dashboard")
        self.root.geometry("900x540")
        self.root.minsize(820, 460)
        self.root.configure(bg=BG)

        self._bridge_proc: subprocess.Popen | None = None
        self._cloudflared_proc: subprocess.Popen | None = None
        self._kabu_ok: bool = False

        self._stop_event = threading.Event()

        self._build_ui()
        self._start_status_poller()
        self._tick_clock()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────
    # UI 構築
    # ─────────────────────────────────────────
    def _build_ui(self) -> None:
        # ───── ヘッダー ─────
        header = tk.Frame(self.root, bg=BG, height=60)
        header.pack(fill=tk.X, padx=14, pady=(12, 6))
        header.pack_propagate(False)

        # タイトル (左)
        tk.Label(
            header,
            text="N225BrokerBridge",
            font=("Segoe UI Semibold", 16),
            bg=BG, fg=ACCENT,
        ).pack(side=tk.LEFT, padx=(0, 16))

        # 時計 (右)
        self.lbl_clock = tk.Label(
            header,
            text="--:--:--",
            font=("Consolas", 14),
            bg=BG, fg=FG_DIM,
        )
        self.lbl_clock.pack(side=tk.RIGHT, padx=(0, 4))

        # ステータス LED 群 (中央)
        status_box = tk.Frame(header, bg=BG)
        status_box.pack(side=tk.LEFT, fill=tk.Y)
        self.led_kabu, self.lbl_kabu = self._make_status_led(status_box, "kabu")
        self.led_bridge, self.lbl_bridge = self._make_status_led(status_box, "Bridge")
        self.led_tunnel, self.lbl_tunnel = self._make_status_led(status_box, "Tunnel")

        # ───── 3 カード横並び ─────
        cards = tk.Frame(self.root, bg=BG)
        cards.pack(fill=tk.X, padx=14, pady=(6, 8))

        # カード 1: 朝のルーティーン
        card1 = self._make_card(cards, "1. 朝のルーティーン", PURPLE)
        card1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        self.btn_tv_launch = self._make_card_button(
            card1, "  📊  TradingView 起動", self._on_tv_launch, ACCENT,
        )
        self.btn_tv_launch.pack(fill=tk.X, padx=10, pady=(8, 4))
        self.btn_analyze = self._make_card_button(
            card1, "  🤖  株式分析実行", self._on_analyze, ACCENT,
        )
        self.btn_analyze.pack(fill=tk.X, padx=10, pady=4)
        tk.Frame(card1, bg=PANEL_BG, height=4).pack()   # 余白

        # カード 2: 本番起動
        card2 = self._make_card(cards, "2. 本番起動", GREEN)
        card2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
        self.btn_production_start = self._make_card_button(
            card2, "  🚀  起動", self._on_production_start, GREEN,
        )
        self.btn_production_start.pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(
            card2,
            text="cloudflared → ブリッジ\nを連動起動",
            font=("Segoe UI", 9),
            bg=PANEL_BG, fg=FG_DIM,
            justify=tk.CENTER,
        ).pack(fill=tk.X, padx=10, pady=(2, 8))

        # カード 3: 停止
        card3 = self._make_card(cards, "3. 停止", RED)
        card3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        self.btn_production_stop = self._make_card_button(
            card3, "  ⏹  停止", self._on_production_stop, RED,
        )
        self.btn_production_stop.pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(
            card3,
            text="ブリッジ → cloudflared\nを連動停止",
            font=("Segoe UI", 9),
            bg=PANEL_BG, fg=FG_DIM,
            justify=tk.CENTER,
        ).pack(fill=tk.X, padx=10, pady=(2, 8))

        # ───── ログ ─────
        log_wrap = tk.Frame(self.root, bg=BG)
        log_wrap.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))

        log_header = tk.Frame(log_wrap, bg=PANEL_BG_HI, height=24)
        log_header.pack(fill=tk.X)
        log_header.pack_propagate(False)
        tk.Label(
            log_header,
            text="  操作ログ",
            font=("Segoe UI Semibold", 9),
            bg=PANEL_BG_HI, fg=FG_DIM,
            anchor=tk.W,
        ).pack(side=tk.LEFT, fill=tk.Y)

        self.log = scrolledtext.ScrolledText(
            log_wrap, bg="#16161e", fg=FG,
            font=("Consolas", 9),
            insertbackground=FG, borderwidth=0,
            wrap=tk.WORD, height=10,
        )
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.tag_config("info", foreground=FG)
        self.log.tag_config("dim", foreground=FG_DIM)
        self.log.tag_config("accent", foreground=ACCENT)
        self.log.tag_config("success", foreground=GREEN)
        self.log.tag_config("warn", foreground=YELLOW)
        self.log.tag_config("error", foreground=RED)

    def _make_status_led(self, parent: tk.Frame, label: str) -> tuple[tk.Canvas, tk.Label]:
        """ヘッダー用のステータス LED + ラベル"""
        row = tk.Frame(parent, bg=BG)
        row.pack(side=tk.LEFT, padx=(0, 18))

        canvas = tk.Canvas(row, width=14, height=14, bg=BG, highlightthickness=0)
        canvas.pack(side=tk.LEFT, padx=(0, 6))
        canvas.create_oval(2, 2, 12, 12, fill=LED_OFF, outline="")

        lbl = tk.Label(
            row, text=label,
            font=("Segoe UI", 10),
            bg=BG, fg=FG,
        )
        lbl.pack(side=tk.LEFT)
        return canvas, lbl

    def _set_led(self, canvas: tk.Canvas, color: str) -> None:
        canvas.delete("all")
        canvas.create_oval(2, 2, 12, 12, fill=color, outline="")

    def _make_card(self, parent: tk.Frame, title: str, title_color: str) -> tk.Frame:
        """カードの外枠を作成"""
        outer = tk.Frame(parent, bg=PANEL_BG, bd=0, highlightthickness=0)
        # タイトルバー
        header = tk.Frame(outer, bg=PANEL_BG_HI, height=28)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        # タイトルの左に色マーカー
        tk.Frame(header, bg=title_color, width=3).pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(
            header,
            text=f"  {title}",
            font=("Segoe UI Semibold", 10),
            bg=PANEL_BG_HI, fg=FG,
            anchor=tk.W,
        ).pack(side=tk.LEFT, fill=tk.Y, expand=True)
        return outer

    def _make_card_button(
        self, parent: tk.Frame, text: str, command, base_color: str,
    ) -> tk.Button:
        """カード内のボタン (ホバー演出付き)"""
        btn = tk.Button(
            parent, text=text, command=command,
            font=("Segoe UI", 11),
            bg=base_color, fg="#1a1b26",
            activebackground=base_color, activeforeground="#1a1b26",
            relief=tk.FLAT, padx=10, pady=10,
            cursor="hand2",
            anchor=tk.W,
        )
        # ホバー時の色明るく
        def on_enter(_e, b=btn, c=base_color):
            b.configure(bg=self._brighten(c, 0.15))
        def on_leave(_e, b=btn, c=base_color):
            b.configure(bg=c)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    @staticmethod
    def _brighten(hex_color: str, ratio: float) -> str:
        """16進色を ratio (0..1) 分明るくする"""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r = min(255, int(r + (255 - r) * ratio))
        g = min(255, int(g + (255 - g) * ratio))
        b = min(255, int(b + (255 - b) * ratio))
        return f"#{r:02x}{g:02x}{b:02x}"

    # ─────────────────────────────────────────
    # ログ
    # ─────────────────────────────────────────
    def _log(self, msg: str, level: str = "info") -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        def append():
            self.log.insert(tk.END, f"[{timestamp}] ", "dim")
            self.log.insert(tk.END, f"{msg}\n", level)
            self.log.see(tk.END)
        self.root.after(0, append)

    # ─────────────────────────────────────────
    # 時計 (1 秒更新)
    # ─────────────────────────────────────────
    def _tick_clock(self) -> None:
        if self._stop_event.is_set():
            return
        self.lbl_clock.config(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    # ─────────────────────────────────────────
    # ステータスポーラー (3 秒間隔)
    # ─────────────────────────────────────────
    def _start_status_poller(self) -> None:
        threading.Thread(target=self._status_poll_loop, daemon=True).start()

    def _status_poll_loop(self) -> None:
        while not self._stop_event.is_set():
            self._update_kabu_status()
            self._update_proc_status()
            self._stop_event.wait(3.0)

    def _update_kabu_status(self) -> None:
        try:
            req = urllib.request.Request(KABU_HEALTH_URL, method="GET")
            with urllib.request.urlopen(req, timeout=KABU_HEALTH_TIMEOUT_SEC) as resp:
                _ = resp.status
            ok = True
        except urllib.error.HTTPError:
            ok = True
        except Exception:
            ok = False

        prev = self._kabu_ok
        self._kabu_ok = ok
        color = LED_ON if ok else LED_OFF
        self.root.after(0, lambda c=color: self._set_led(self.led_kabu, c))
        # 状態変化時のみログ
        if prev != ok:
            if ok:
                self._log("kabu Station 接続中", "success")
            else:
                self._log("kabu Station 接続不可", "warn")

    def _update_proc_status(self) -> None:
        bridge_on = self._bridge_proc is not None and self._bridge_proc.poll() is None
        cf_on = self._cloudflared_proc is not None and self._cloudflared_proc.poll() is None
        self.root.after(0, lambda: self._set_led(self.led_bridge, LED_ON if bridge_on else LED_OFF))
        self.root.after(0, lambda: self._set_led(self.led_tunnel, LED_ON if cf_on else LED_OFF))

    # ─────────────────────────────────────────
    # 1. TradingView デバッグモード起動
    # ─────────────────────────────────────────
    def _on_tv_launch(self) -> None:
        self.btn_tv_launch.config(state=tk.DISABLED)
        self._log("TradingView をデバッグモードで起動します...", "accent")
        threading.Thread(target=self._tv_launch_worker, daemon=True).start()

    def _tv_launch_worker(self) -> None:
        try:
            if not os.path.exists(TV_LAUNCH_PS1):
                self._log(f"スクリプトが見つかりません: {TV_LAUNCH_PS1}", "error")
                return
            if not os.path.exists(PWSH_EXE):
                self._log(f"pwsh.exe が見つかりません: {PWSH_EXE}", "error")
                return

            self._log("  PowerShell スクリプト実行中...", "dim")
            proc = subprocess.Popen(
                [PWSH_EXE, "-ExecutionPolicy", "Bypass", "-File", TV_LAUNCH_PS1],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            success = False
            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                if line.startswith("ERROR"):
                    self._log(f"  {line}", "error")
                elif "成功" in line or "Success" in line.lower() or "CDP 接続成功" in line:
                    self._log(f"  {line}", "success")
                    success = True
                else:
                    self._log(f"  {line}", "dim")
            proc.wait()

            if proc.returncode != 0 and not success:
                self._log("TradingView 起動が失敗しました", "error")
            else:
                self._log("TradingView 起動完了", "success")
        except Exception as e:
            self._log(f"TradingView 起動エラー: {e}", "error")
        finally:
            self.root.after(0, lambda: self.btn_tv_launch.config(state=tk.NORMAL))

    # ─────────────────────────────────────────
    # 2. 株式分析実行
    # ─────────────────────────────────────────
    def _on_analyze(self) -> None:
        self.btn_analyze.config(state=tk.DISABLED)
        self._log("株式分析を開始します...", "accent")
        threading.Thread(target=self._analyze_worker, daemon=True).start()

    def _check_tv_cdp(self) -> bool:
        try:
            req = urllib.request.Request(TV_CDP_URL, method="GET")
            with urllib.request.urlopen(req, timeout=TV_CDP_TIMEOUT_SEC) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _analyze_worker(self) -> None:
        try:
            if not self._check_tv_cdp():
                self._log("ERROR: TradingView がデバッグモードで起動していません", "error")
                self._log("  「TradingView 起動」ボタンを先に押してください", "error")
                return
            self._log("  TradingView CDP 接続確認 OK", "dim")

            env = os.environ.copy()
            for k in CLAUDE_ENV_VARS_TO_STRIP:
                env.pop(k, None)
            # Claude Code が内部 Bash ツールを PowerShell として認識するように SHELL を固定。
            # 未指定だと Git Bash が拾われ、Sort-Object / Select-Object 等の PowerShell 構文が
            # bash 上で実行され `command not found` + Windows パス崩壊 (\U \t \N 消費) で失敗する。
            env["SHELL"] = PWSH_EXE

            today_str = datetime.now().strftime("%Y-%m-%d")
            analysis_path = os.path.join(ANALYSIS_DIR, f"{today_str}.md")
            click_time = datetime.now().timestamp()

            if not os.path.exists(PWSH_EXE):
                self._log(f"ERROR: pwsh.exe が見つかりません: {PWSH_EXE}", "error")
                return

            self._log("Claude Code を新ウィンドウで起動します (/analyze 自動投入)", "accent")
            self._log("  別ウィンドウで分析が進みます。完了したらウィンドウを閉じてください", "dim")
            try:
                proc = subprocess.Popen(
                    [PWSH_EXE, "-NoExit", "-NoLogo", "-Command", "claude /analyze"],
                    cwd=BASE_DIR,
                    env=env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            except FileNotFoundError:
                self._log(f"ERROR: pwsh.exe が起動できません: {PWSH_EXE}", "error")
                return
            except Exception as e:
                self._log(f"Claude 起動エラー: {e}", "error")
                return

            self._log(f"  pwsh プロセス起動 (PID={proc.pid})", "dim")

            proc.wait()
            self._log(f"分析ウィンドウ終了 (exit={proc.returncode})", "dim")

            if not os.path.exists(analysis_path):
                self._log(
                    "本日分の分析ファイルが見つかりません — プレビューはスキップします",
                    "warn",
                )
                self._log(f"  期待パス: {analysis_path}", "dim")
                return

            analysis_fresh = os.path.getmtime(analysis_path) >= click_time
            if analysis_fresh:
                self._log("分析完了 — ブラウザでプレビューを開きます...", "success")
            else:
                self._log(
                    "本日のファイルは存在しますが今回のクリック以前の更新です — 既存内容でプレビューします",
                    "warn",
                )
                self._log(f"  対象パス: {analysis_path}", "dim")
            if not os.path.exists(VENV_PYTHON):
                self._log(f"  venv python が見つかりません: {VENV_PYTHON}", "error")
                return
            if not os.path.exists(PREVIEW_PY):
                self._log(f"  preview スクリプトが見つかりません: {PREVIEW_PY}", "error")
                return
            try:
                preview_proc = subprocess.Popen(
                    [VENV_PYTHON, PREVIEW_PY],
                    cwd=BASE_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                preview_out, _ = preview_proc.communicate(timeout=20)
                if preview_proc.returncode == 0:
                    self._log("  プレビュー起動完了", "success")
                    for line in (preview_out or "").splitlines():
                        if line.strip():
                            self._log(f"    {line.strip()}", "dim")
                else:
                    self._log(
                        f"  プレビュースクリプトが異常終了 (exit={preview_proc.returncode})",
                        "error",
                    )
                    for line in (preview_out or "").splitlines():
                        if line.strip():
                            self._log(f"    {line.strip()}", "error")
            except subprocess.TimeoutExpired:
                self._log("  プレビュー起動タイムアウト (20s)", "warn")
            except Exception as e:
                self._log(f"プレビュー起動エラー: {e}", "error")
        finally:
            self.root.after(0, lambda: self.btn_analyze.config(state=tk.NORMAL))

    # ─────────────────────────────────────────
    # 3. 本番起動 (cloudflared → ブリッジ 連動)
    # ─────────────────────────────────────────
    def _on_production_start(self) -> None:
        self.btn_production_start.config(state=tk.DISABLED)
        self._log("本番起動を開始します (cloudflared → ブリッジ)", "accent")
        threading.Thread(target=self._production_start_worker, daemon=True).start()

    def _production_start_worker(self) -> None:
        try:
            # 1. cloudflared
            cf_ok = self._start_cloudflared()
            if not cf_ok:
                self._log("cloudflared 起動失敗のため、ブリッジは起動しません", "error")
                return

            # 2. ブリッジ
            br_ok = self._start_bridge()
            if not br_ok:
                self._log("ブリッジ起動失敗", "error")
                return

            self._log("本番起動完了", "success")
        finally:
            self.root.after(0, lambda: self.btn_production_start.config(state=tk.NORMAL))

    def _start_cloudflared(self) -> bool:
        if self._cloudflared_proc is not None and self._cloudflared_proc.poll() is None:
            self._log("  cloudflared は既に起動中です", "warn")
            return True
        self._log(f"  cloudflared 起動: tunnel run {CLOUDFLARED_TUNNEL_NAME}", "dim")
        try:
            self._cloudflared_proc = subprocess.Popen(
                [CLOUDFLARED_EXE, "tunnel", "run", CLOUDFLARED_TUNNEL_NAME],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            self._log(f"  cloudflared OK (PID={self._cloudflared_proc.pid})", "success")
            threading.Thread(
                target=self._drain_stdout,
                args=(self._cloudflared_proc,),
                daemon=True,
            ).start()
            return True
        except FileNotFoundError:
            self._log(f"  cloudflared が見つかりません: {CLOUDFLARED_EXE}", "error")
            return False
        except Exception as e:
            self._log(f"  cloudflared 起動失敗: {e}", "error")
            return False

    def _start_bridge(self) -> bool:
        if self._bridge_proc is not None and self._bridge_proc.poll() is None:
            self._log("  ブリッジは既に起動中です", "warn")
            return True
        if not os.path.exists(BRIDGE_EXE):
            self._log(f"  ブリッジ実行ファイルが見つかりません: {BRIDGE_EXE}", "error")
            return False
        try:
            self._bridge_proc = subprocess.Popen(
                [BRIDGE_EXE],
                cwd=os.path.dirname(BRIDGE_EXE),
            )
            self._log(f"  ブリッジ OK (PID={self._bridge_proc.pid})", "success")
            return True
        except Exception as e:
            self._log(f"  ブリッジ起動失敗: {e}", "error")
            return False

    # ─────────────────────────────────────────
    # 4. 停止 (ブリッジ → cloudflared 連動)
    # ─────────────────────────────────────────
    def _on_production_stop(self) -> None:
        self.btn_production_stop.config(state=tk.DISABLED)
        self._log("停止します (ブリッジ → cloudflared)", "warn")
        threading.Thread(target=self._production_stop_worker, daemon=True).start()

    def _production_stop_worker(self) -> None:
        try:
            self._stop_bridge()
            self._stop_cloudflared()
            self._log("停止完了", "success")
        finally:
            self.root.after(0, lambda: self.btn_production_stop.config(state=tk.NORMAL))

    def _stop_bridge(self) -> None:
        if self._bridge_proc is None or self._bridge_proc.poll() is not None:
            self._bridge_proc = None
            return
        self._log("  ブリッジを停止...", "dim")
        self._terminate_proc(self._bridge_proc)
        self._bridge_proc = None
        self._log("  ブリッジ停止完了", "success")

    def _stop_cloudflared(self) -> None:
        if self._cloudflared_proc is None or self._cloudflared_proc.poll() is not None:
            self._cloudflared_proc = None
            return
        self._log("  cloudflared を停止...", "dim")
        self._terminate_proc(self._cloudflared_proc)
        self._cloudflared_proc = None
        self._log("  cloudflared 停止完了", "success")

    # ─────────────────────────────────────────
    # 共通: プロセス停止 / 標準出力捨て
    # ─────────────────────────────────────────
    @staticmethod
    def _terminate_proc(proc: subprocess.Popen) -> None:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        except Exception:
            pass

    @staticmethod
    def _drain_stdout(proc: subprocess.Popen) -> None:
        try:
            for _ in proc.stdout or []:
                pass
        except Exception:
            pass

    # ─────────────────────────────────────────
    # 終了処理
    # ─────────────────────────────────────────
    def _on_close(self) -> None:
        running = []
        if self._bridge_proc is not None and self._bridge_proc.poll() is None:
            running.append("Bridge")
        if self._cloudflared_proc is not None and self._cloudflared_proc.poll() is None:
            running.append("cloudflared")
        if running:
            from tkinter import messagebox
            ans = messagebox.askyesno(
                "確認",
                f"{' / '.join(running)} が起動中です。停止して終了しますか？\n"
                "「いいえ」を選ぶとプロセスを残したままダッシュボードのみ終了します。",
            )
            if ans:
                self._production_stop_worker()
        self._stop_event.set()
        self.root.destroy()


def main() -> int:
    root = tk.Tk()
    _ = BrokerBridgeDashboard(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
