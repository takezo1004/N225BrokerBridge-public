"""
AI 分析シナリオの精度を過去データと照合して計測する。

各分析日について:
    1. パースで抽出した scenario/支持/抵抗を取得
    2. target_date の 1 分足実データを取得（history_csv から）
    3. 実際の day_open / day_high / day_low / day_close を計算
    4. 精度指標を算出
       - bias_correct: 予測方向と実績終値方向が一致？
       - top_scenario_hit: 最高確率シナリオの target レンジに引けが入った？
       - support_held: 最強 support でバウンスした？（test_hit = low touched, held = close back above）
       - resistance_rejected: 最強 resistance で拒絶された？

出力: CSV 風のサマリー + 集計指標
"""

from __future__ import annotations
import os
import sys
import pandas as pd
from datetime import datetime, date
from pathlib import Path

SB_DIR = Path(__file__).resolve().parents[2] / "N225StrategyBuilder"
sys.path.insert(0, str(SB_DIR))

from scenario_parser import parse_analysis
from feature_engine_py.ohlc_loader import load_from_dir


def get_day_ohlc(df_1m: pd.DataFrame, target_date: date,
                 day_start_hour: int = 8, day_start_min: int = 45,
                 day_end_hour: int = 15, day_end_min: int = 45) -> dict:
    """target_date の日中セッション（8:45-15:45）の OHLC を取得。"""
    start = pd.Timestamp(target_date.year, target_date.month, target_date.day,
                         day_start_hour, day_start_min)
    end   = pd.Timestamp(target_date.year, target_date.month, target_date.day,
                         day_end_hour, day_end_min)
    day = df_1m.loc[start:end]
    if len(day) == 0:
        return None
    return {
        "open":  float(day["open"].iloc[0]),
        "high":  float(day["high"].max()),
        "low":   float(day["low"].min()),
        "close": float(day["close"].iloc[-1]),
        "bar_count": len(day),
    }


def evaluate_day(parsed: dict, day_ohlc: dict) -> dict:
    """1 日分の予測 vs 実績を評価。"""
    result = {
        "target_date": parsed["target_date"],
        "base_price": parsed["base_price"],
        "bias_predicted": parsed["bias"],
        "n_resistances": len(parsed["resistances"]),
        "n_supports": len(parsed["supports"]),
        "n_scenarios": len(parsed["scenarios"]),
    }
    if day_ohlc is None:
        result["data_available"] = False
        return result

    result.update(day_ohlc)
    o, h, l, c = day_ohlc["open"], day_ohlc["high"], day_ohlc["low"], day_ohlc["close"]
    result["data_available"] = True

    # 実績方向
    change = c - o
    actual_dir = "up" if change > 50 else "down" if change < -50 else "range"
    result["actual_direction"] = actual_dir
    result["change"] = change

    # Bias 一致判定
    bias_map = {"bullish": "up", "bearish": "down", "neutral": "range"}
    predicted_dir = bias_map.get(parsed["bias"], "range")
    result["bias_correct"] = (predicted_dir == actual_dir)

    # トップシナリオ
    if parsed["scenarios"]:
        top = max(parsed["scenarios"], key=lambda s: s["probability"])
        result["top_scenario_name"] = top["name"]
        result["top_scenario_prob"] = top["probability"]
        result["top_scenario_direction"] = top["direction"]
        result["top_scenario_correct"] = (top["direction"] == actual_dir)

        # 全シナリオのうち、終値が target レンジに収まるものを探す
        matching_scenarios = []
        for s in parsed["scenarios"]:
            if s["target_low"] is not None and s["target_high"] is not None:
                if s["target_low"] - 50 <= c <= s["target_high"] + 50:
                    matching_scenarios.append(s["name"])
        result["closing_in_scenario"] = ", ".join(matching_scenarios)
    else:
        result["top_scenario_name"] = None
        result["top_scenario_correct"] = None

    # Resistance test: 最強 Resistance (highest strength, then closest to base)
    if parsed["resistances"]:
        strong_r = max(parsed["resistances"], key=lambda r: (r["strength"], -r["price_low"]))
        r_price = (strong_r["price_low"] + strong_r["price_high"]) / 2
        result["key_resistance"] = r_price
        # Tested? high reached within 0.1% of resistance
        tested = h >= r_price * 0.999
        # Rejected? close finished below resistance
        rejected = tested and c < r_price
        result["resistance_tested"] = tested
        result["resistance_rejected"] = rejected

    # Support test
    if parsed["supports"]:
        strong_s = max(parsed["supports"], key=lambda s: (s["strength"], s["price_low"]))
        s_price = (strong_s["price_low"] + strong_s["price_high"]) / 2
        result["key_support"] = s_price
        tested = l <= s_price * 1.001
        held = tested and c > s_price
        result["support_tested"] = tested
        result["support_held"] = held

    return result


def main():
    # 1. 分析ファイル全てをパース
    daily_dir = Path(__file__).resolve().parents[1] / "analyses"
    md_files = sorted(daily_dir.glob("*.md"))
    parsed_all = [parse_analysis(str(f)) for f in md_files]

    # 2. 1 分足データロード（2026 のみで十分）
    hist_dir = SB_DIR / "history_csv"
    print("[load] reading 1-minute history data...")
    df_1m = load_from_dir(hist_dir, pattern="N225minif_2026.xlsx", verbose=False)
    print(f"[load] bars: {len(df_1m):,}, range: {df_1m.index[0]} ~ {df_1m.index[-1]}")

    # 3. 各分析の精度評価
    results = []
    for p in parsed_all:
        if not p["target_date"]:
            continue
        tgt = datetime.strptime(p["target_date"], "%Y-%m-%d").date()
        # 当日データがなければスキップ
        day_ohlc = get_day_ohlc(df_1m, tgt)
        r = evaluate_day(p, day_ohlc)
        results.append(r)

    # 4. 集計レポート
    print("\n" + "=" * 100)
    print(f"{'target':12} | {'open':>7} | {'high':>7} | {'low':>7} | {'close':>7} | "
          f"{'Δ':>5} | {'actual':6} | {'bias_pred':10} | {'bias_ok':7} | "
          f"{'top_scen':8} | {'scen_ok':7} | {'closing_scen':15}")
    print("-" * 100)
    for r in results:
        if not r["data_available"]:
            print(f"{r['target_date']:12} | --- no data ---")
            continue
        bias_ok = "OK" if r.get("bias_correct") else "NG"
        scen_ok = "OK" if r.get("top_scenario_correct") else ("NG" if r.get("top_scenario_correct") is not None else "-")
        top_scen = str(r.get("top_scenario_direction", "-"))[:8]
        closing = (r.get("closing_in_scenario") or "")[:15]
        print(f"{r['target_date']:12} | {r['open']:>7.0f} | {r['high']:>7.0f} | "
              f"{r['low']:>7.0f} | {r['close']:>7.0f} | {r['change']:>+5.0f} | "
              f"{r['actual_direction']:6} | {r['bias_predicted']:10} | {bias_ok:7} | "
              f"{top_scen:8} | {scen_ok:7} | {closing:15}")

    # 集計
    valid = [r for r in results if r["data_available"]]
    bias_results = [r["bias_correct"] for r in valid if r.get("bias_correct") is not None]
    scen_results = [r["top_scenario_correct"] for r in valid if r.get("top_scenario_correct") is not None]
    res_results  = [r for r in valid if r.get("resistance_tested")]
    sup_results  = [r for r in valid if r.get("support_tested")]

    print("\n" + "=" * 70)
    print("集計サマリー")
    print("=" * 70)
    print(f"総分析日数: {len(results)}")
    print(f"データ有効: {len(valid)}")
    if bias_results:
        print(f"Bias 正解率: {sum(bias_results)}/{len(bias_results)} "
              f"= {sum(bias_results)/len(bias_results)*100:.1f}%")
    if scen_results:
        print(f"トップシナリオ正解率: {sum(scen_results)}/{len(scen_results)} "
              f"= {sum(scen_results)/len(scen_results)*100:.1f}%")
    if res_results:
        rejected = [r for r in res_results if r.get("resistance_rejected")]
        print(f"主要抵抗 テスト時 拒絶率: {len(rejected)}/{len(res_results)} "
              f"= {len(rejected)/len(res_results)*100:.1f}%")
    if sup_results:
        held = [r for r in sup_results if r.get("support_held")]
        print(f"主要支持 テスト時 保持率: {len(held)}/{len(sup_results)} "
              f"= {len(held)/len(sup_results)*100:.1f}%")

    return results


if __name__ == "__main__":
    main()
