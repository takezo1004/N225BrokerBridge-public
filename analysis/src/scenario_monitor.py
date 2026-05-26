"""
シナリオ並列監視型バックテスト
==============================
AI が生成した A/B/C シナリオを並列に監視し、トリガー条件が発動したら
そのシナリオに従ってトレードを実行する（裁量トレード模擬）。

シナリオのトリガータイプ:
    - break_above: 特定価格を上抜け → Long
    - break_below: 特定価格を下抜け → Short
    - range:       価格帯内での逆張り（上限で売り/下限で買い）
"""

from __future__ import annotations
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import pandas as pd

SB_DIR = Path(__file__).resolve().parents[2] / "N225StrategyBuilder"
sys.path.insert(0, str(SB_DIR))

from scenario_parser import parse_analysis
from feature_engine_py.ohlc_loader import load_from_dir


def scenario_to_trigger(scenario: dict, base_price: float,
                         sup_levels: list, res_levels: list) -> Optional[dict]:
    """
    シナリオ dict をトリガー実行ルールに変換。
    Returns:
        {
          "direction": "long"/"short"/"range",
          "trigger_level": float,    # 発動価格
          "trigger_type": "break_above"/"break_below"/"touch",
          "tp": float,
          "sl": float,
        }
    """
    d = scenario["direction"]
    tl, th = scenario.get("target_low"), scenario.get("target_high")

    # 抵抗・支持の最強を取得
    def _strongest(levels):
        if not levels: return None
        return max(levels, key=lambda x: (x["strength"], -abs(x["price_low"] - base_price) if base_price else 0))

    r = _strongest(res_levels)  # 最強抵抗
    s = _strongest(sup_levels)  # 最強支持

    if d == "up":
        # 上昇シナリオ: 最弱抵抗（最近い抵抗）を上抜けでロング
        nearest_r = min([x for x in res_levels
                         if base_price is None or x["price_low"] >= base_price - 100],
                        key=lambda x: x["price_low"]) if res_levels else None
        if nearest_r is None:
            return None
        trigger_price = nearest_r["price_low"]
        tp = th or (trigger_price * 1.008)  # +0.8% デフォルト
        sl = s["price_high"] if s else (trigger_price * 0.995)
        return {"direction": "long", "trigger_level": trigger_price,
                "trigger_type": "break_above", "tp": tp, "sl": sl,
                "name": scenario["name"], "prob": scenario["probability"]}

    if d == "down":
        # 下落シナリオ: 最近い支持を下抜けでショート
        nearest_s = max([x for x in sup_levels
                         if base_price is None or x["price_high"] <= base_price + 100],
                        key=lambda x: x["price_high"]) if sup_levels else None
        if nearest_s is None:
            return None
        trigger_price = nearest_s["price_high"]
        tp = tl or (trigger_price * 0.992)
        sl = r["price_low"] if r else (trigger_price * 1.005)
        return {"direction": "short", "trigger_level": trigger_price,
                "trigger_type": "break_below", "tp": tp, "sl": sl,
                "name": scenario["name"], "prob": scenario["probability"]}

    if d == "range" and tl is not None and th is not None:
        # レンジシナリオ: 上限タッチで売り、下限タッチで買い
        return {"direction": "range", "range_low": tl, "range_high": th,
                "trigger_type": "range",
                "name": scenario["name"], "prob": scenario["probability"]}

    return None


def execute_scenario_trade(df_min: pd.DataFrame, trigger: dict,
                            commission_pt: float = 1.0) -> list[dict]:
    """
    1 日分の 1 分足データで trigger を監視しトレード実行。
    """
    trades = []
    if df_min is None or len(df_min) == 0:
        return trades

    if trigger["trigger_type"] in ("break_above", "break_below"):
        level = trigger["trigger_level"]
        is_break_above = trigger["trigger_type"] == "break_above"
        triggered = False
        entry_idx = None
        for i, (ts, bar) in enumerate(df_min.iterrows()):
            if not triggered:
                # 発動判定
                if is_break_above and bar["close"] > level and (i == 0 or df_min.iloc[i-1]["close"] <= level):
                    triggered = True
                    entry_idx = i
                elif not is_break_above and bar["close"] < level and (i == 0 or df_min.iloc[i-1]["close"] >= level):
                    triggered = True
                    entry_idx = i
                if triggered:
                    entry_price = bar["close"]
                    tp = trigger["tp"]
                    sl = trigger["sl"]
                    direction = 1 if is_break_above else -1
                    # 以降のバーで TP/SL を判定
                    exit_info = None
                    for j in range(i + 1, min(i + 300, len(df_min))):  # 最大 5 時間
                        bj = df_min.iloc[j]
                        if direction == 1 and bj["high"] >= tp:
                            exit_info = (tp, "tp", j)
                            break
                        if direction == -1 and bj["low"] <= tp:
                            exit_info = (tp, "tp", j)
                            break
                        if direction == 1 and bj["low"] <= sl:
                            exit_info = (sl, "sl", j)
                            break
                        if direction == -1 and bj["high"] >= sl:
                            exit_info = (sl, "sl", j)
                            break
                    if exit_info is None:
                        exit_price = df_min.iloc[min(i + 299, len(df_min) - 1)]["close"]
                        exit_info = (exit_price, "timeout", min(i + 299, len(df_min) - 1))
                    exit_price, reason, exit_idx = exit_info
                    raw_pnl = (exit_price - entry_price) if direction == 1 else (entry_price - exit_price)
                    trades.append({
                        "scenario": trigger["name"],
                        "direction": trigger["direction"],
                        "entry_time": df_min.index[entry_idx],
                        "entry_price": entry_price,
                        "exit_time": df_min.index[exit_idx],
                        "exit_price": exit_price,
                        "exit_reason": reason,
                        "trigger_level": level,
                        "tp": tp, "sl": sl,
                        "pnl": raw_pnl - commission_pt,
                    })
                    break  # 1 日 1 回のみ発動

    elif trigger["trigger_type"] == "range":
        # レンジ: 上端タッチで売り、下端タッチで買い（簡易版）
        lo = trigger["range_low"]
        hi = trigger["range_high"]
        mid = (lo + hi) / 2
        for i in range(len(df_min)):
            bar = df_min.iloc[i]
            # 上端タッチで売り、TP=下端、SL=上端+0.3%
            if bar["high"] >= hi and bar["close"] < hi:
                entry_price = hi
                direction = -1
                tp = lo
                sl = hi * 1.003
            elif bar["low"] <= lo and bar["close"] > lo:
                entry_price = lo
                direction = 1
                tp = hi
                sl = lo * 0.997
            else:
                continue
            # exit
            for j in range(i + 1, min(i + 180, len(df_min))):
                bj = df_min.iloc[j]
                if direction == 1 and bj["high"] >= tp:
                    pnl = tp - entry_price - commission_pt
                    trades.append({"scenario": trigger["name"], "direction": "range_long",
                                   "entry_price": entry_price, "exit_price": tp,
                                   "pnl": pnl, "exit_reason": "tp",
                                   "entry_time": df_min.index[i], "exit_time": df_min.index[j]})
                    break
                if direction == -1 and bj["low"] <= tp:
                    pnl = entry_price - tp - commission_pt
                    trades.append({"scenario": trigger["name"], "direction": "range_short",
                                   "entry_price": entry_price, "exit_price": tp,
                                   "pnl": pnl, "exit_reason": "tp",
                                   "entry_time": df_min.index[i], "exit_time": df_min.index[j]})
                    break
                if direction == 1 and bj["low"] <= sl:
                    pnl = sl - entry_price - commission_pt
                    trades.append({"scenario": trigger["name"], "direction": "range_long",
                                   "entry_price": entry_price, "exit_price": sl,
                                   "pnl": pnl, "exit_reason": "sl",
                                   "entry_time": df_min.index[i], "exit_time": df_min.index[j]})
                    break
                if direction == -1 and bj["high"] >= sl:
                    pnl = entry_price - sl - commission_pt
                    trades.append({"scenario": trigger["name"], "direction": "range_short",
                                   "entry_price": entry_price, "exit_price": sl,
                                   "pnl": pnl, "exit_reason": "sl",
                                   "entry_time": df_min.index[i], "exit_time": df_min.index[j]})
                    break
            break  # 1 日 1 回（簡易版）

    return trades


def main():
    daily_dir = Path(__file__).resolve().parents[1] / "analyses"
    md_files = sorted(daily_dir.glob("*.md"))

    hist_dir = SB_DIR / "history_csv"
    print("[load] 1-min data...")
    df_1m = load_from_dir(hist_dir, pattern="N225minif_2026.xlsx", verbose=False)

    all_trades = []
    for f in md_files:
        parsed = parse_analysis(str(f))
        if not parsed["target_date"]:
            continue
        tgt = datetime.strptime(parsed["target_date"], "%Y-%m-%d").date()

        start = pd.Timestamp(tgt.year, tgt.month, tgt.day, 8, 45)
        end   = pd.Timestamp(tgt.year, tgt.month, tgt.day, 15, 45)
        df_day = df_1m.loc[start:end]
        if len(df_day) == 0:
            print(f"  {f.name} -> {tgt}: no day data, skip")
            continue

        print(f"\n=== {f.name} -> {tgt} ({len(df_day)} bars) ===")

        triggers = []
        for s in parsed["scenarios"]:
            t = scenario_to_trigger(s, parsed["base_price"],
                                    parsed["supports"], parsed["resistances"])
            if t:
                triggers.append(t)
                print(f"  Trigger: {t['name'][:30]:30} | {t['direction']:6} | "
                      f"type={t['trigger_type']:13}")

        # 各トリガーを並列実行
        day_trades = []
        for t in triggers:
            trades = execute_scenario_trade(df_day, t, commission_pt=1.0)
            for tr in trades:
                tr["target_date"] = str(tgt)
                day_trades.append(tr)

        if day_trades:
            for tr in day_trades:
                print(f"    TRADE: {tr['scenario'][:25]:25} entry={tr['entry_price']:.0f} "
                      f"exit={tr['exit_price']:.0f} reason={tr['exit_reason']:7} "
                      f"pnl={tr['pnl']:+6.1f}pt")
        else:
            print(f"    No triggers fired")

        all_trades.extend(day_trades)

    # 集計
    if all_trades:
        print("\n" + "=" * 70)
        print(f"シナリオ並列監視 総合成績")
        print("=" * 70)
        total_pnl = sum(t["pnl"] for t in all_trades)
        wins = [t for t in all_trades if t["pnl"] > 0]
        losses = [t for t in all_trades if t["pnl"] <= 0]
        gw = sum(t["pnl"] for t in wins)
        gl = abs(sum(t["pnl"] for t in losses))
        pf = gw / gl if gl > 0 else float("inf")
        print(f"総トレード数: {len(all_trades)}")
        print(f"勝率: {len(wins)}/{len(all_trades)} = {len(wins)/len(all_trades)*100:.1f}%")
        print(f"PF: {pf:.2f}")
        print(f"合計 PnL: {total_pnl:+.0f}pt (手数料込み 1pt/trade)")
        print(f"評価日数: {len(set(t['target_date'] for t in all_trades))}")

        # 日別
        print("\n日別トレード:")
        from collections import defaultdict
        by_day = defaultdict(list)
        for t in all_trades:
            by_day[t["target_date"]].append(t)
        for d, ts in sorted(by_day.items()):
            day_pnl = sum(t["pnl"] for t in ts)
            print(f"  {d}: {len(ts)} trades, PnL={day_pnl:+.1f}pt")


if __name__ == "__main__":
    main()
