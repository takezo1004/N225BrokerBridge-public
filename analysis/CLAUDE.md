# N225LLMAdvisor — Claude Code 設定

## プロジェクト概要

日経225ミニ先物を **LLM 駆動のシナリオ分析** でトレードする実験的プロジェクト。
既存の機械的戦略（`N225StrategyBuilder` 等）とは独立して開発・運用する。

**哲学**: 裁量トレーダーの「朝の分析 → シナリオ並列監視 → 夜の反省」というサイクルを
LLM で自動化し、累積された知識で翌朝の分析を強化する。

---

## 既存プロジェクトとの関係

| 項目 | 既存プロジェクト群 | **本プロジェクト（N225LLMAdvisor）** |
|------|-----------------|----------------------------------|
| 場所 | `N225StrategyBuilder/` / `N225SignalTrader/` 等 | `N225LLMAdvisor/` |
| パラダイム | ルールベース・機械学習 | LLM シナリオ駆動 |
| 成功指標 | PF / WR / DD | シナリオ正解率・キャリブレーション |
| 状態 | L1 スキャルプ PF 1.61 検証済み | 初期セットアップ完了、データ蓄積期 |
| 干渉 | なし（互いに独立） | なし |
| 共有資産 | TradingView MCP, `history_csv/`, N225OrderBridge | 同左（参照のみ） |

**両者は並行運用される前提**。干渉せず、将来的には両方のシグナルを比較・統合する可能性あり。

---

## フォルダ構成

```
N225LLMAdvisor/
├── CLAUDE.md                     # 本ファイル
├── README.md                     # 概要・セットアップ手順
├── analyses/                     # 朝分析（YAML 付きレポート）
│   └── YYYY-MM-DD.md
├── results/                      # 当日結果記録
│   └── YYYY-MM-DD_result.md
├── reviews/                      # 振り返りメモ（Q1-Q5）
│   └── YYYY-MM-DD_review.md
├── memory/                       # 累積知識
│   ├── market_memory.md          # 直近 30 日の市場特性
│   ├── pattern_accuracy.md       # AI 予測正解率の集計
│   └── lessons.md                # 累積された学び
├── templates/                    # 記入テンプレ
│   ├── daily_analysis_template.md
│   ├── result_template.md
│   └── review_template.md
├── src/                          # Python 実装
│   ├── scenario_parser.py        # YAML/Markdown パーサー
│   ├── scenario_monitor.py       # シナリオ並列監視・機械執行シミュレート
│   └── accuracy_tester.py        # 予測精度の定量評価
└── docs/                         # 設計書・分析レポート
    └── (将来の拡張用)
```

---

## 日次サイクル（運用ルール）

```
07:30-08:30  朝分析    /analyze 実行
             ↓        前日 memory/ を読込 → 今日のシナリオ (A/B/C) 生成
             出力     analyses/YYYY-MM-DD.md（YAML ブロック含む）

08:45-15:45  日中監視  シナリオ A/B/C を並列監視
             トレード  発動したシナリオに従い執行
             （将来: Groq Llama3.1-8b で 5 分毎判定）

15:50-16:30  引け後   結果記録 → results/YYYY-MM-DD_result.md
             振り返り → reviews/YYYY-MM-DD_review.md（Q1-Q5）

週末         memory/   market_memory.md / pattern_accuracy.md / lessons.md を更新
             プロンプト改善の議論

翌朝         /analyze  累積された memory/ を読み込み再実行
```

---

## トリガーフレーズ

### 「本日の分析をお願いします」「朝の分析」
→ `/analyze` コマンドを実行。出力先は `N225LLMAdvisor/analyses/YYYY-MM-DD.md`

### 「結果を記録します」
→ `templates/result_template.md` をコピーして `results/YYYY-MM-DD_result.md` 作成支援

### 「振り返りをします」
→ `templates/review_template.md` をコピーして `reviews/YYYY-MM-DD_review.md` 作成支援

### 「市場メモリを更新」「週次更新」
→ `memory/market_memory.md` と `memory/pattern_accuracy.md` を集計・更新

### 「精度計測」
→ `python src/accuracy_tester.py` を実行し、直近分析の正解率を集計

---

## LLM の役割分担

| フェーズ | 使用 LLM | 備考 |
|---------|----------|------|
| 朝の詳細分析 | Claude Code (`/analyze`) | 人が起動、TradingView MCP でチャート取得 |
| 引け後分析 | Claude Code | 手動または自動化（将来） |
| 日中 5 分毎判定 | **Groq llama-3.1-8b-instant** | 既存 `N225SignalTrader/src/llm/groq_client.py` を拡張 |
| 夜間 10 分毎判定 | **Groq llama-3.1-8b-instant** | 同上 |

---

## 重要ルール

### データ分離
- `N225LLMAdvisor/` 配下は本プロジェクト専用
- 既存の `N225StrategyBuilder/` 等のコードは**参照のみ**（import OK、書き込みはしない）
- 共有資産: `history_csv/`, TradingView MCP, N225OrderBridge（将来）

### テンプレート厳守
- `daily_analysis_template.md` の YAML セクションは**フィールド名を変更しない**（機械パース対象）
- `result_template.md` の YAML 部分も同様

### 累積知識の信頼度
- `lessons.md` の信頼度は観察回数で昇格：
  - 1-2 回: low
  - 3-4 回: medium
  - 5 回以上: high
- 信頼度 medium 以上のみ朝分析に反映

### スクショの保存先
既存と共用: `N225McpServer/screenshots/`

---

## 現在のフェーズ

**Phase 0: インフラ構築**（2026-04-23 完了）
- ディレクトリ構造・テンプレ・CLAUDE.md・memory 雛形 作成

**Phase 1: データ蓄積**（2026-04-24 〜）
- 毎朝 `/analyze` を新フォーマットで実行
- 毎日 result / review を記入
- 週末に memory 更新

**Phase 2: 精度評価**（〜2026-05-15）
- 20 営業日分のデータで `accuracy_tester.py` 実行
- パターン別正解率・キャリブレーション確認

**Phase 3: Groq 拡張**（Phase 2 合格後）
- 既存 `signal_judge.py` を拡張し、5 分毎 LLM 判定モジュール実装
- バックテスト後に導入判断

**Phase 4: 執行統合**（Phase 3 検証後）
- N225OrderBridge 経由の発注接続

---

## 参考リンク

- ルート CLAUDE.md: `../CLAUDE.md`
- 既存 LLM クライアント: `../N225SignalTrader/src/llm/groq_client.py`
- Feature Engine Python ポート: `../N225StrategyBuilder/feature_engine_py/`
- 1 分足履歴データ: `../N225StrategyBuilder/history_csv/`

## 運用改善の判断基準

週次・月次で運用を振り返る際は、以下のドキュメントを参照すること:
- `docs/improvement_judgment_guide.md`

このドキュメントには、改善判断の基準・フローチャート・
優先度表が記載されている。運用開始30日間は「致命的問題」以外の
改善は行わない。データ蓄積を優先する。
