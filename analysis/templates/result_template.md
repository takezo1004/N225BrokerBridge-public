# 当日結果記録テンプレート

**このテンプレートの使い方**:
- 引け後（15:50 以降）または夜間開始時にこのテンプレートを `results/YYYY-MM-DD_result.md` にコピーして記入
- YAML 部分は機械パースされるため**フィールド名は変更しないこと**
- `---` で挟まれた YAML 前置き部分と Markdown 説明部分の 2 部構成

---

```yaml
meta:
  date: "YYYY-MM-DD"           # 対象日
  day_open: 0                   # 日中セッション始値 (8:45)
  day_high: 0                   # 日中セッション高値 (8:45-15:45)
  day_low:  0                   # 日中セッション安値
  day_close: 0                  # 日中セッション終値 (15:45)
  change_pts: 0                 # day_close - day_open
  change_pct: 0.0               # change / day_open
  atr_5m_avg: 0                 # 当日 5 分足 ATR 平均
  night_high: null              # 夜間セッション高値（翌朝記入）
  night_low:  null              # 夜間セッション安値
  volatility: "low/normal/high/extreme"   # 体感ボラ

# 朝の予測に対する実績マッチング
scenarios_predicted:
  A:
    name: "上昇ブレイク"
    probability_predicted: 0.0
    trigger_level: 0            # 発動価格
    fired: false                # 発動したか
    fire_time: null             # 発動時刻
    hit_tp: false               # TP 到達したか
    final_direction: "up/down/range"   # 終局の方向
    note: ""                    # 具体コメント
  B:
    name: "レンジ"
    probability_predicted: 0.0
    range_low: 0
    range_high: 0
    fired: false
    note: ""
  C:
    name: "下落ブレイク"
    probability_predicted: 0.0
    trigger_level: 0
    fired: false
    fire_time: null
    hit_tp: false
    final_direction: ""
    note: ""

winning_scenario: "A/B/C/none"   # 最も妥当だったシナリオ
prediction_accuracy: "high/medium/low"   # 主観評価

# 実行したトレード（全件）
trades_executed:
  - entry_time: "HH:MM"
    side: "long/short"
    scenario_ref: "A/B/C/manual"
    entry_price: 0
    exit_time: "HH:MM"
    exit_price: 0
    exit_reason: "tp/sl/time/manual/ew_turn"
    pnl_pts: 0
    pnl_yen_per_lot: 0
    lots: 1
    comment: ""

pnl_total_pts: 0                 # 全トレード合計
pnl_total_yen_per_lot: 0         # 1 枚あたり合計
n_trades: 0
n_wins: 0
n_losses: 0

# 外部要因（あれば）
market_events:
  - time: "HH:MM"
    event: ""                    # CPI, 日銀, 米雇用統計 etc.
    impact: "low/medium/high"
    observed_reaction: ""

related_markets:
  nq_session:  { open: 0, close: 0, change_pct: 0.0 }   # ナスダック夜間
  dow_session: { open: 0, close: 0, change_pct: 0.0 }   # ダウ夜間（任意）
  crude_oil:   { close: 0, change_pct: 0.0 }             # 原油日足
  usd_jpy:     { open: 0, close: 0, change_pct: 0.0 }   # ドル円（任意）
```

---

## 人間向けメモ（自由記述）

### 今日の動きサマリー
（1-3 行で今日の相場を言語化）

### 予測と実績の乖離ポイント
- 予測した `A（確率○○%）` は... （発動/未発動）、理由は...
- 予測した `B` は... 
- 予測した `C` は...

### 上手くいった判断
- 

### 改善余地
- 

### 翌日への持ち越し事項
- 

---

## スクリーンショット

- 日足引け後: `screenshots/n225_daily_YYYY-MM-DD_close.png`
- 5分足全日: `screenshots/n225_5m_YYYY-MM-DD_full.png`
