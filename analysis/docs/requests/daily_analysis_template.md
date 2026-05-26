# 日経225 デイリーマーケット分析
**日付**: {{DATE}}
**分析時刻**: 市場オープン前
**分析者**: Claude Code

---

## ■ 前日海外市況サマリー

### 米株主要指数（前日終値・騰落率）
- ナスダック100（NQ1!）: 
- S&P500（ES1!）: 
- ダウ平均: 
- 半導体ETF（SOXX）: 

### セクター別の動意
- 半導体: 
- テック・大型グロース: 
- その他注目セクター: 

### 動意材料
- 決算: 
- 要人発言: 
- 経済指標: 

### 為替
- USD/JPY 前日終値: 
- DXY: 

### 今日の日経への波及見立て
- 

---

## ■ 前日シナリオの当落点検

前営業日 `analyses/YYYY-MM-DD.md` のシナリオ A/B/C 結果:

- ✅ 当たった: 
- ❌ 外した: 
- 学び（今日の分析に反映）: 

> reviews/ が記入されていない場合は、本セクションで簡易点検を行う。

---

## ■ ファンダメンタル分析

### 地政学リスク
- 中東・イラン情勢: 
- ウクライナ情勢: 
- 台湾海峡・東アジア: 
- その他: 

### 米国経済
- FRB金利政策・FOMC期待: 
- インフレ（CPI/PCE）: 
- 雇用統計: 
- 景気後退リスク: 

### 日本経済
- 日銀金融政策: 
- 円相場（USD/JPY）の意味合い: 
- 国内景気指標: 

### 米国株式
- ナスダック・S&P500の動向: 
- テクノロジーセクター: 
- 半導体（SOXX/SOX）: 

### コモディティ・エネルギー
- 原油 WTI: 
- 金: 
- OPEC+動向: 

### 金利・為替
- 米10年利回り: 
- ドルインデックス（DXY）: 
- USD/JPY: 

### リスクセンチメント
- VIX: 
- リスクオン/オフの評価: 

### アジア市場
- ハンセン: 
- その他アジア株: 

### 本日の経済指標
| 時刻（JST） | 指標 | 重要度 | 予想 | 前回 |
|------|------|------|------|------|
| | | | | |

### その他重要ニュース
- 

---

## ■ チャート分析

### 【日足】N225 Daily

| 日付 | 始値 | 高値 | 安値 | 終値 | 出来高 | 備考 |
|------|------|------|------|------|------|------|
| | | | | | | |

**日足の判断**:
- トレンド: 
- ATR(20): 
- 直近サポート: 
- 直近レジスタンス: 
- 出来高の特徴: 

### 【4時間足】N225 4H
- 直近の流れ: 
- ATR(20): 
- サポート: 
- レジスタンス: 
- 出来高: 

### 【1時間足】N225 1H
- 直近の流れ: 
- サポート: 
- レジスタンス: 

### 【15分足】N225 15M
- 直近の流れ: 
- パターン: 
- 本日の起点: 

### 全時間軸トレンド一致・乖離まとめ
- 

---

## ■ 関連銘柄分析

### ナスダック100（CME_MINI:NQ1!）日足
- トレンド: 
- 直近の動向: 
- 日経との相関: 

### S&P500（CME_MINI:ES1!）日足
- トレンド: 
- NQ との比較（テック vs 全体）: 

### USD/JPY（OANDA:USDJPY）日足
- トレンド: 
- 「円安=日経プラス」が成立しているか: 

### 半導体ETF（NASDAQ:SOXX）日足
- トレンド: 
- 日経テック銘柄への影響: 

---

## ■ 本日の重要価格水準
| レベル | 価格 | 強度 | 意味 |
|--------|------|------|------|
| 上値抵抗③ | | ★★★ | |
| 上値抵抗② | | ★★ | |
| 上値抵抗① | | ★ | |
| 現在値 | | - | |
| サポート① | | ★ | |
| サポート② | | ★★ | |
| サポート③ | | ★★★ | |

---

## ■ 総合判断・本日の方向性

| シナリオ | 確率 | 価格目標 | 条件 |
|----------|------|----------|------|
| A: | % | | |
| B: | % | | |
| C: | % | | |

**本日結論**:

---

## ■ スクリーンショット
- [日足](../screenshots/{{DATE}}/n225_daily.png)
- [4時間足](../screenshots/{{DATE}}/n225_4h.png)
- [1時間足](../screenshots/{{DATE}}/n225_1h.png)
- [15分足](../screenshots/{{DATE}}/n225_15m.png)
- [NQ1! 日足](../screenshots/{{DATE}}/nq_daily.png)
- [ES1! 日足](../screenshots/{{DATE}}/sp_daily.png)
- [USD/JPY 日足](../screenshots/{{DATE}}/usdjpy_daily.png)
- [SOXX 日足](../screenshots/{{DATE}}/soxx_daily.png)

---

## ■ 実行可能シナリオ（YAML、機械執行用・正本）

> **このセクションが本分析の正本**。Markdown 部分は人間用の要約。
> フィールド名は固定（機械パース対象）。
> `scenario_parser.py` がこの YAML を読む。

```yaml
meta:
  analysis_date: "{{DATE}}"              # 分析を行なった日
  target_date: "{{DATE}}"                # 対象セッション日（土日祝の場合は次の営業日）
  base_price: 0                           # 分析時点の参考価格（日経225ミニ）
  analysis_time: "pre_open"               # pre_open / intraday / post_close / pre_night
  atr_reference: 0                        # 日足 ATR(20)（TP/SL 設計の目安）
  atr_4h: 0                                # 4時間足 ATR(20)
  confidence: 0.5                         # この分析自体の自信度（0.0-1.0）
  market_status: "open"                   # open / holiday_open / closed

scenarios:
  - id: "A"
    name: ""
    probability: 0.0                      # 0.0-1.0
    direction: "long"                     # long / short / range / neutral
    entry:
      type: "break_above"                 # break_above / break_below / touch_rejection / zone_reversal
      level: 0                             # 発動価格
      confirmation: "close_5m_above"      # 発動確認方法
      time_window: ["09:00", "13:00"]     # 有効時間帯（JST "HH:MM"）
    exits:
      tp1: { price: 0, size_pct: 50 }     # 第1利確
      tp2: { price: 0, size_pct: 50 }     # 第2利確
      sl:  { price: 0, type: "hard" }     # 損切
      invalidation: ""                     # シナリオ無効化条件
    thesis: ""                              # 発動の根拠・前提（1-2 文）

  - id: "B"
    name: ""
    probability: 0.0
    direction: "range"
    range: { low: 0, high: 0 }
    sub_triggers:
      - name: "上限逆張り"
        entry: { type: "touch_rejection", level: 0, confirm: "close_1m_below" }
        exits: { tp: 0, sl: 0 }
      - name: "下限押し目買い"
        entry: { type: "touch_rejection", level: 0, confirm: "close_1m_above" }
        exits: { tp: 0, sl: 0 }
    invalidation: ""
    thesis: ""

  - id: "C"
    name: ""
    probability: 0.0
    direction: "short"
    entry:
      type: "break_below"
      level: 0
      confirmation: "close_5m_below"
      time_window: ["09:00", "15:00"]
    exits:
      tp1: { price: 0, size_pct: 50 }
      tp2: { price: 0, size_pct: 50 }
      sl:  { price: 0, type: "hard" }
      invalidation: ""
    thesis: ""

key_levels:
  resistances:
    - { price: 0, strength: 1, note: "" }   # strength: 1(弱) / 2(中) / 3(強)
    - { price: 0, strength: 2, note: "" }
    - { price: 0, strength: 3, note: "" }
  supports:
    - { price: 0, strength: 1, note: "" }
    - { price: 0, strength: 2, note: "" }
    - { price: 0, strength: 3, note: "" }

related_markets:                           # Tier 1 + Tier 2 銘柄の現在値・前日比
  nq:        { last: 0, change_pct: 0.0, role: "tech_correlation" }
  sp:        { last: 0, change_pct: 0.0, role: "broad_market" }
  usdjpy:    { last: 0, change_pct: 0.0, role: "exporter_impact" }
  soxx:      { last: 0, change_pct: 0.0, role: "semi_leading_indicator" }
  crude_oil: { last: 0, change_pct: 0.0, role: "geopolitics_inflation" }
  gold:      { last: 0, change_pct: 0.0, role: "safe_haven" }
  dxy:       { last: 0, change_pct: 0.0, role: "dollar_strength" }
  us10y:     { last: 0, change_pct: 0.0, role: "discount_rate" }
  vix:       { last: 0, change_pct: 0.0, role: "risk_sentiment" }
  hsi:       { last: 0, change_pct: 0.0, role: "asia_sentiment" }

risk_flags:
  volatility_regime: "normal"             # low / normal / high / extreme
  event_risk:                              # 本日の経済指標
    - { time: "HH:MM", event: "", impact: "high" }   # impact: low / medium / high
  market_regime: ""                         # bullish_trend / bearish_trend / range / transition
  skip_trading_if: []                      # ["extreme_volatility", "major_news_1h_before"]

preferred_bias: "neutral"                 # bullish / bearish / neutral / neutral_to_bullish ...
avoid_bias: null                           # 避けたい方向

prior_day_review:                          # 前日シナリオ点検（reviews/ が空でも記入）
  hit_scenario: ""                          # A/B/C/none
  miss_reason: ""                           # 簡易な敗因分析
  carry_over: ""                            # 今日への引き継ぎ事項

references:
  market_memory_version: "memory/market_memory.md"
  lessons_applied: []                      # 参照した学び ID（例: ["L001", "L003"]、なければ []）
  prior_analysis: "analyses/YYYY-MM-DD.md"  # 前営業日の分析ファイル
```

---

## ■ 連動ワークフロー

当日結果記録 → 振り返り → 翌朝への引き継ぎの日次サイクル:

1. **引け後（15:50-16:30）**: `templates/result_template.md` をコピーして `results/{{DATE}}_result.md` に記入
2. **その後**: `review_template.md` をコピーして `reviews/{{DATE}}_review.md` に 5 つの問いで振り返り
3. **週末**: `memory/market_memory.md` と `memory/pattern_accuracy.md` を更新
4. **翌朝の `/analyze`**: 上記 memory 群と前日 analyses を読み込み、今日の分析へ反映
