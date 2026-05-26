# N225LLMAdvisor

日経225ミニ先物を **LLM 駆動のシナリオ分析** でトレードする実験的システム。  
既存の機械的戦略（`N225StrategyBuilder`）とは独立した新プロジェクトです。

## コンセプト

```
裁量トレーダーの日常:
  朝   チャート分析 → A/B/C シナリオ想定 → トレードプラン確定
  日中 シナリオ並列監視 → 発動したもの執行
  夜   結果振り返り → 学びを蓄積 → 翌朝反映

これを LLM で自動化・累積する。
```

## クイックスタート

### 毎朝（市場オープン前 07:30-08:30）

```bash
# Claude Code で
/analyze
```

→ `analyses/YYYY-MM-DD.md` が生成される（YAML ブロック含む）

### 引け後（15:50-16:30）

```bash
# 当日結果記録
cp templates/result_template.md results/YYYY-MM-DD_result.md
# 編集して埋める

# 振り返り
cp templates/review_template.md reviews/YYYY-MM-DD_review.md
# Q1-Q5 に回答
```

### 週末

- `memory/market_memory.md` を更新（直近 30 日の特性追記）
- `memory/pattern_accuracy.md` を集計
- `memory/lessons.md` に新規項目を追加

## 精度計測

```bash
cd N225LLMAdvisor
python src/accuracy_tester.py
```

蓄積された分析を実データと照合し、以下を出力：
- Bias 正解率
- トップシナリオ正解率
- 主要サポート/抵抗のテスト・拒絶率

## ディレクトリ構成

| 場所 | 用途 |
|------|------|
| `analyses/` | 朝分析（自動生成、YAML 付き） |
| `results/` | 当日結果（手動記入） |
| `reviews/` | 振り返り（手動記入） |
| `memory/` | 累積知識（週次更新） |
| `templates/` | 記入テンプレ |
| `src/` | Python ツール |
| `docs/` | 設計書 |

## 日次サイクルと学習ループ

```
朝分析（memory/ 読込）
     ↓
YAML シナリオ生成（A/B/C）
     ↓
日中トレード実行
     ↓
引け後 result.md 記入
     ↓
review.md 5 問で振り返り
     ↓
週末: memory/ 更新
     ↓
翌朝へ（累積情報で強化）
```

## 既存プロジェクトとの関係

- **独立運用**: `N225StrategyBuilder`（Long スキャルプ PF 1.61）と並行して稼働
- **共有資産**: `../N225StrategyBuilder/history_csv/` (1 分足データ), TradingView MCP
- **将来統合**: 両方のシグナルを比較・併用する可能性

## フェーズ計画

| Phase | 内容 | 時期 |
|-------|------|------|
| 0 | インフラ構築 | 2026-04-23 完了 |
| 1 | データ蓄積（毎日運用） | 2026-04-24 〜 |
| 2 | 精度評価（20 営業日） | 〜 2026-05-15 |
| 3 | Groq 5 分毎判定 拡張 | Phase 2 合格後 |
| 4 | N225OrderBridge 執行統合 | Phase 3 検証後 |

## 詳細は `CLAUDE.md` を参照
