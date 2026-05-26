# 依頼書: scenario_parser.py の YAML パーサー化

**バージョン**: 1.0
**作成日**: 2026-05-03
**対象**: N225LLMAdvisor

---

## 1. 目的

現状の `src/scenario_parser.py` は Markdown 表を正規表現でパースしているが、Skill 改修・テンプレート改修により **YAML ブロックが分析の正本** となった。これに合わせて parser を YAML ベースに刷新する。

## 2. 現状の問題

- Markdown 表のパースは表現の揺れに脆弱(「A: 上昇継続」「A:上昇」等で正規表現が壊れる)
- TP/SL・確認方法・有効時間帯などの詳細情報を表から取れない
- 一方、`daily_analysis_template.md` の YAML スキーマには TP/SL・時間窓・無効化条件など豊富な情報がある
- 機械執行(将来の N225OrderBridge 連携)には YAML の情報量が必須

## 3. 変更後の動作

### 3.1 入力

- `analyses/YYYY-MM-DD.md` を入力(現状と同じ)

### 3.2 処理

1. ファイル全体を読み込む
2. YAML ブロック(```yaml ... ``` で囲まれた部分)を抽出
   - 複数ブロックある場合は **最後のブロック** を採用(YAML が「実行可能シナリオ」セクションの末尾にあるため)
   - または、YAML ブロック前のヘッダーに「実行可能シナリオ」「機械執行用」等の文字列があるブロックを優先
3. `yaml.safe_load()` でパース
4. パース結果を以下のスキーマで返す(後続処理が使いやすい形に整形)

### 3.3 出力(返り値の dict)

```python
{
    "file": str,                      # 入力ファイルパス
    "analysis_date": str,             # YYYY-MM-DD(YAML の meta.analysis_date)
    "target_date": str,               # YYYY-MM-DD(YAML の meta.target_date)
    "base_price": float,              # YAML の meta.base_price
    "atr_reference": float,           # YAML の meta.atr_reference
    "confidence": float,              # YAML の meta.confidence
    "market_status": str,             # open / holiday_open / closed
    "scenarios": [                    # YAML の scenarios 配列をそのまま
        {
            "id": "A",
            "name": str,
            "probability": float,
            "direction": str,
            "entry": {...},
            "exits": {...},
            "thesis": str,
            ...
        },
        ...
    ],
    "key_levels": {                   # YAML の key_levels をそのまま
        "resistances": [...],
        "supports": [...],
    },
    "related_markets": {...},         # YAML の related_markets
    "risk_flags": {...},              # YAML の risk_flags
    "bias": str,                      # 最も確率の高いシナリオから導出(後方互換)
}
```

### 3.4 後方互換性

既存呼び出し元(`scenario_monitor.py`、`accuracy_tester.py` など)が壊れないよう、現状の返り値キー(`bias`、`scenarios`、`resistances`、`supports`、`base_price`、`analysis_date`、`target_date`)は維持する。

新スキーマでは `key_levels.resistances` だが、トップレベルにも `resistances` を残す(後方互換のエイリアス)。

## 4. target_date 計算の修正

現状のコード:

```python
while target_date.weekday() >= 5:  # 5=土, 6=日
    target_date = target_date + timedelta(days=1)
```

これでは祝日がスキップされず、祝日取引非実施日に予測対象を当ててしまう。修正:

```python
# 土日に加えて、祝日取引非実施日もスキップ
HOLIDAY_NON_TRADING = {
    # JPX 公式の「実施しない」リスト
    # 2026年: 1/2, 11/23, 12/31
    # 2027年: 9/20, 12/31
    date(2026, 1, 2),
    date(2026, 11, 23),
    date(2026, 12, 31),
    date(2027, 9, 20),
    date(2027, 12, 31),
}

while (target_date.weekday() >= 5 or target_date in HOLIDAY_NON_TRADING):
    target_date = target_date + timedelta(days=1)
```

> **注意**: 祝日取引実施日(2026-05-04 等)は通常の営業日として扱う(スキップしない)。スキップするのは「祝日取引非実施日」のみ。
> リストは Skill の祝日判定リスト(`analyze.md` §0)と同期させる。

## 5. エラーハンドリング

- YAML ブロックが見つからない: 旧形式(Markdown 表のみ)へフォールバック、警告ログ
- YAML パースエラー: ファイルパスとエラー内容を出力して例外
- 必須キー欠落(`meta.analysis_date`、`scenarios` 等): 警告ログ + 取得できた範囲で返す

## 6. テスト

- `analyses/` 配下の既存ファイル全件でパース成功を確認(後方互換)
- 新フォーマットのテストファイル(YAML ブロック付き)を作成してパース成功を確認
- target_date 計算: 金曜分析→月曜、祝日取引非実施日跨ぎ、祝日取引実施日(スキップしない)の3パターン

## 7. 報告

本依頼書末尾に `## 8. 実装結果(YYYY-MM-DD)` として追記。

含める内容:
- 要約
- 変更したファイル一覧(`src/scenario_parser.py` 含む)
- 後方互換性の確認結果(既存 analyses/ 全件パース可能か)
- target_date 計算の動作確認結果
- 既知の制約・継続課題

## 8. 関連

- Skill: `c:/Users/takao2/N225TradingSystem/N225LLMAdvisor/.claude/commands/analyze.md`(Skill 改修版)
- テンプレート: `templates/daily_analysis_template.md`(YAML スキーマの正本)
- 現状の parser: `src/scenario_parser.py`
- 影響を受ける後続処理: `src/scenario_monitor.py`、`src/accuracy_tester.py`
