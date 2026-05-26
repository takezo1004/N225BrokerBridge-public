"""
AI 分析ファイル(Markdown) から構造化シナリオを抽出するパーサー

抽出項目:
    - prediction_date: 予測対象日
    - base_price: 分析時点の参考価格
    - resistances: [{tier: 1/2/3, price_low: float, price_high: float, strength: int}]
    - supports:    同上
    - scenarios:   [{name: str, probability: float, target_low: float, target_high: float, condition: str}]
    - bias:        "bullish"/"bearish"/"neutral"
"""

from __future__ import annotations
import re
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


def _extract_price_range(text: str) -> tuple[Optional[float], Optional[float]]:
    """文字列から価格範囲を抽出（例: "59,500〜59,715" や "60,110" → (low, high)）。"""
    # コンマ除去した数値を全て取得
    nums = re.findall(r"(\d{2,3}(?:,\d{3})*(?:\.\d+)?|\d{4,6})", text)
    parsed = []
    for n in nums:
        try:
            v = float(n.replace(",", ""))
            if 10000 < v < 100000:  # N225 プライスレンジ
                parsed.append(v)
        except ValueError:
            pass
    if not parsed:
        return (None, None)
    if len(parsed) == 1:
        return (parsed[0], parsed[0])
    return (min(parsed), max(parsed))


def _count_stars(text: str) -> int:
    """★の数を数える（強度）。"""
    return text.count("★")


def parse_analysis(md_path: str) -> dict:
    """Markdown 分析ファイルを構造化 dict に変換。"""
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    # ファイル名から日付を抽出
    fname = Path(md_path).stem  # e.g. "2026-04-22"
    try:
        analysis_date = datetime.strptime(fname, "%Y-%m-%d").date()
    except ValueError:
        analysis_date = None

    # 予測対象日の判定
    # "分析時刻" を確認
    if "翌日オープン前" in content:
        target_date = analysis_date + timedelta(days=1) if analysis_date else None
    elif "市場オープン前" in content:
        target_date = analysis_date
    else:
        target_date = analysis_date  # 不明時は同日

    # 週末を次の営業日に（土日はスキップ）
    if target_date is not None:
        while target_date.weekday() >= 5:  # 5=土, 6=日
            target_date = target_date + timedelta(days=1)

    # Base price: 現在値 / ニ___225ミニ (夜間)
    m = re.search(r"日経225ミニ[^\|]*\|\s*\*?\*?(\d{2,3}(?:,\d{3})?(?:\.\d+)?)",
                  content)
    base_price = None
    if m:
        try:
            base_price = float(m.group(1).replace(",", ""))
        except ValueError:
            pass

    # 上値抵抗 / サポート表の行を抽出
    resistances = []
    supports = []

    # パターン1: 上値抵抗①（強）| 価格 | ...
    # パターン2: 第1抵抗 | 価格 | ...
    # パターン3: 上値抵抗①  | 価格 | 説明
    patterns_r = [
        r"上値抵抗[①②③][^\|]*\|\s*\*?\*?([^\|\*]+?)\*?\*?\s*\|[^\|]+\|\s*([★]+)",
        r"上値抵抗[①②③][^\|]*\|\s*\*?\*?([^\|\*]+?)\*?\*?\s*\|",
        r"第(\d)抵抗[^\|]*\|\s*\*?\*?([^\|\*]+?)\*?\*?\s*\|",
    ]
    # まずは ★ 付きパターンを試す
    for m in re.finditer(patterns_r[0], content):
        price_text = m.group(1).strip()
        stars = _count_stars(m.group(2))
        lo, hi = _extract_price_range(price_text)
        if lo is not None:
            resistances.append({"price_low": lo, "price_high": hi,
                                "strength": stars})

    # なければパターン2
    if not resistances:
        for m in re.finditer(patterns_r[1], content):
            price_text = m.group(1).strip()
            lo, hi = _extract_price_range(price_text)
            if lo is not None and 10000 < lo < 100000:
                resistances.append({"price_low": lo, "price_high": hi,
                                    "strength": 2})

    # なければパターン3 (第N抵抗)
    if not resistances:
        for m in re.finditer(patterns_r[2], content):
            price_text = m.group(2).strip()
            lo, hi = _extract_price_range(price_text)
            if lo is not None:
                resistances.append({"price_low": lo, "price_high": hi,
                                    "strength": 2})

    # 同様に support
    patterns_s = [
        r"サポート[①②③][^\|]*\|\s*\*?\*?([^\|\*]+?)\*?\*?\s*\|[^\|]+\|\s*([★]+)",
        r"サポート[①②③][^\|]*\|\s*\*?\*?([^\|\*]+?)\*?\*?\s*\|",
        r"第(\d)支持[^\|]*\|\s*\*?\*?([^\|\*]+?)\*?\*?\s*\|",
    ]
    for m in re.finditer(patterns_s[0], content):
        price_text = m.group(1).strip()
        stars = _count_stars(m.group(2))
        lo, hi = _extract_price_range(price_text)
        if lo is not None:
            supports.append({"price_low": lo, "price_high": hi,
                             "strength": stars})
    if not supports:
        for m in re.finditer(patterns_s[1], content):
            price_text = m.group(1).strip()
            lo, hi = _extract_price_range(price_text)
            if lo is not None:
                supports.append({"price_low": lo, "price_high": hi,
                                 "strength": 2})
    if not supports:
        for m in re.finditer(patterns_s[2], content):
            price_text = m.group(2).strip()
            lo, hi = _extract_price_range(price_text)
            if lo is not None:
                supports.append({"price_low": lo, "price_high": hi,
                                 "strength": 2})

    # シナリオ（A/B/C または 1/2/3）
    # パターン: | A: 上昇継続 | 40% | 59,500〜59,715 | 条件 |
    scenario_pattern = re.compile(
        r"\|\s*([ABC][\s:：][^|]+?)\s*\|\s*\*?\*?(\d+)\s*%\*?\*?\s*\|\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|"
    )
    scenarios = []
    for m in scenario_pattern.finditer(content):
        name = m.group(1).strip()
        prob = int(m.group(2)) / 100.0
        target_text = m.group(3).strip()
        condition = m.group(4).strip()
        lo, hi = _extract_price_range(target_text)
        is_up = any(kw in name for kw in ["上昇", "Bull", "ブレイク"])
        is_down = any(kw in name for kw in ["下落", "Bear", "急落", "ドロップ"])
        is_range = any(kw in name for kw in ["レンジ", "横ばい", "もみ合い"])
        direction = "up" if is_up else "down" if is_down else "range" if is_range else "?"
        scenarios.append({
            "name": name,
            "probability": prob,
            "target_low": lo,
            "target_high": hi,
            "direction": direction,
            "condition": condition,
        })

    # Bias 判定（最も確率の高いシナリオから）
    if scenarios:
        top = max(scenarios, key=lambda s: s["probability"])
        bias = {"up": "bullish", "down": "bearish",
                "range": "neutral", "?": "neutral"}[top["direction"]]
    else:
        bias = "neutral"

    return {
        "file": md_path,
        "analysis_date": str(analysis_date) if analysis_date else None,
        "target_date": str(target_date) if target_date else None,
        "base_price": base_price,
        "resistances": resistances,
        "supports": supports,
        "scenarios": scenarios,
        "bias": bias,
    }


if __name__ == "__main__":
    import glob
    import json

    dir_ = Path(__file__).resolve().parents[1] / "analyses"
    files = sorted(dir_.glob("*.md"))
    for f in files:
        result = parse_analysis(str(f))
        print(f"\n=== {f.name} ===")
        print(f"  predict target: {result['target_date']}")
        print(f"  base_price: {result['base_price']}")
        print(f"  bias: {result['bias']}")
        print(f"  resistances: {result['resistances']}")
        print(f"  supports: {result['supports']}")
        print(f"  scenarios:")
        for s in result['scenarios']:
            print(f"    {s['probability']*100:.0f}% [{s['direction']}] "
                  f"target={s['target_low']}-{s['target_high']} : {s['name']}")
