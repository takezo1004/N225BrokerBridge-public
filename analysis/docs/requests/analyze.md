TradingViewを使って日経225ミニ先物（OSE:NK225M1!）の本日の市場分析を実施してください。以下の手順で行います。

## 手順

### 0. 営業日判定（最初に実行）

以下の条件で「分析する日」かどうかを判定する。判定結果に応じてフローが変わる。

```
土曜日・日曜日:
    → §10 (休場日処理) へジャンプ。分析しない。

平日（月〜金、祝日でない日）:
    → 通常分析を実行。

祝日（国民の祝日）:
    → 祝日取引実施日リストに含まれる日: 通常分析を実行
    → 含まれない日: §10 (休場日処理) へジャンプ。分析しない。

1月1日〜3日、12月31日:
    → §10 (休場日処理) へジャンプ。分析しない。
```

#### 祝日取引実施日リスト

JPX 公式: https://www.jpx.co.jp/derivatives/rules/holidaytrading/index.html
最終更新: 2026-05-03

**2026年（確定）**:
- 実施する: 1/12, 2/11, 2/23, 3/20, 4/29, 5/4, 5/5, 5/6, 7/20, 8/11, 9/21, 9/22, 9/23, 10/12, 11/3
- 実施しない（休場）: 1/2, 11/23（BCPテスト）, 12/31

**2027年（予定）**:
- 実施する: 1/11, 2/11, 2/23, 3/22, 4/29, 5/3, 5/4, 5/5, 7/19, 8/11, 9/23, 10/11, 11/3, 11/23
- 実施しない（休場）: 9/20（BCPテスト）, 12/31

> **メンテナンス**: 毎年2月にJPX公式が翌年予定を、6月・12月に確定版を公表する。年に1回程度このリストを更新する必要がある。Claude / Claude Code に依頼可能。

### 1. 事前コンテキストの読み込み（N225LLMAdvisor フロー）

以下を可能な範囲で読み込み、今日の分析の前提として活用する。**ファイルが空または未作成でも続行する**（蓄積期のため）。

- `N225LLMAdvisor/memory/market_memory.md`: 直近の市場レジーム・観察された同時性
- `N225LLMAdvisor/memory/lessons.md`: 直近の学び（信頼度 medium 以上があれば優先）
- `N225LLMAdvisor/memory/pattern_accuracy.md`: AI 予測の直近キャリブレーション
- 前営業日の `N225LLMAdvisor/reviews/YYYY-MM-DD_review.md` が存在すれば「明日への引き継ぎ事項」を反映
- 前営業日の `N225LLMAdvisor/analyses/YYYY-MM-DD.md` を読み、**前日のシナリオ A/B/C のどれが当たったか / 外したか** を簡易点検（reviews が空でもこの自己点検は行う）

### 2. TradingView 接続確認とデフォルトチャート記録

1. `tv_health_check` を実行
2. **現在のシンボルとタイムフレームを記録**（`chart_get_symbol`, `chart_get_timeframe`）
   - これは分析終了時に元に戻すため。「5分足固定」ではなく実行時の状態を保持する
3. 記録した値を `default_symbol` と `default_timeframe` 変数として保持

### 3. 経済指標カレンダーの確認

本日の主要経済指標発表予定を取得:

- 日本時間で発表される指標（日銀会合、GDP、雇用統計、CPI、機械受注 等）
- 米国時間で発表される指標（CPI、PCE、雇用統計、FOMC、小売売上、ISM 等）
- 各指標の発表時刻（JST 換算）と重要度

取得元: TradingView 経済カレンダー、または `web_search` で「経済指標 カレンダー YYYY-MM-DD」検索

### 4. 現在値・前日比の取得（並行実行）

#### Tier 1（チャート分析対象、5銘柄）

- 日経225ミニ（OSE:NK225M1!）
- ナスダック100先物（CME_MINI:NQ1!）
- S&P500先物（CME_MINI:ES1!）
- USD/JPY（OANDA:USDJPY）
- 半導体ETF SOXX（NASDAQ:SOXX）

#### Tier 2（現在値・前日比のみ、6銘柄）

- 原油 WTI（NYMEX:CL1!）
- 金（COMEX:GC1!）
- ドルインデックス（TVC:DXY）
- 米10年利回り（TVC:US10Y）
- VIX（TVC:VIX）
- ハンセン指数（TVC:HSI）

これらを `quote_get` で並行取得。Tier 2 はチャート分析せず数値のみ。

### 5. 日経225ミニ 各時間軸チャート分析

各時間軸で以下を実施:
- シンボルとタイムフレーム設定
- 直近 OHLCV データ取得
- ATR(20) を取得（TP/SL 距離決定用）
- 出来高分析（直近 N 日平均との比較）
- スクリーンショット保存

#### 5.1 日足分析

- シンボル: OSE:NK225M1!、タイムフレーム: D
- OHLCV: 直近60本
- ATR(20) 取得
- スクリーンショット: `screenshots/YYYY-MM-DD/n225_daily.png`

#### 5.2 4時間足分析

- タイムフレーム: 240
- OHLCV: 直近60本
- ATR(20) 取得
- スクリーンショット: `screenshots/YYYY-MM-DD/n225_4h.png`

#### 5.3 1時間足分析

- タイムフレーム: 60
- OHLCV: 直近60本
- スクリーンショット: `screenshots/YYYY-MM-DD/n225_1h.png`

#### 5.4 15分足分析

- タイムフレーム: 15
- OHLCV: 直近80本
- スクリーンショット: `screenshots/YYYY-MM-DD/n225_15m.png`

### 6. Tier 1 関連銘柄チャート分析

#### 6.1 ナスダック100先物（NQ1!）日足

- シンボル: CME_MINI:NQ1!、タイムフレーム: D
- OHLCV: 直近30本
- スクリーンショット: `screenshots/YYYY-MM-DD/nq_daily.png`

#### 6.2 S&P500先物（ES1!）日足

- シンボル: CME_MINI:ES1!、タイムフレーム: D
- OHLCV: 直近30本
- スクリーンショット: `screenshots/YYYY-MM-DD/sp_daily.png`

#### 6.3 USD/JPY 日足

- シンボル: OANDA:USDJPY、タイムフレーム: D
- OHLCV: 直近30本
- スクリーンショット: `screenshots/YYYY-MM-DD/usdjpy_daily.png`

#### 6.4 半導体ETF（SOXX）日足

- シンボル: NASDAQ:SOXX、タイムフレーム: D
- OHLCV: 直近30本
- スクリーンショット: `screenshots/YYYY-MM-DD/soxx_daily.png`

### 7. 総合分析レポートの作成

以下の構成で作成。**human-readable な Markdown** + **machine-readable な YAML** の二段構成。

#### 7.1 ファンダメンタル分析

株価に影響を与える可能性のある全ての情報を網羅:

- **地政学リスク**: イラン・中東、ウクライナ、台湾海峡、その他
- **米国経済**: FRB金利、インフレ（CPI/PCE）、雇用、景気後退リスク
- **日本経済**: 日銀政策、円相場、国内景気指標
- **米国株式**: NQ・SP500の動向、テクノロジーセクター、半導体
- **コモディティ**: 原油、金、エネルギー政策、OPEC+
- **金利・為替**: 米10年利回り、ドルインデックス、USD/JPY
- **リスクセンチメント**: VIX、その他リスク指標
- **アジア市場**: ハンセン、上海総合（ある程度言及）
- **本日の経済指標**: §3 で取得した発表予定の整理（重要度・発表時刻・JST換算）
- **その他重要ニュース**: 株価に影響しうる全ての要因

#### 7.2 前日海外市況サマリー（新規追加）

- 前日の米株主要指数の終値・騰落率（NQ, SP500, ダウ）
- セクター別騰落（特に半導体・テック）
- 動意材料（決算・要人発言・指標）
- 為替の動き（USD/JPY、DXY）
- これらが今日の日経にどう影響しそうか

#### 7.3 前日シナリオの当落点検（新規追加）

前営業日の `analyses/YYYY-MM-DD.md` を読み、シナリオ A/B/C のどれが当たったかを簡易点検:

- 当たったシナリオ: 
- 外したシナリオ: 
- 学び（今日の分析に反映すべき点）: 

#### 7.4 チャート分析

各時間軸で以下を記述:
- トレンド・サポート・抵抗・重要高値安値
- ATR 値（TP/SL 設計の参考）
- 出来高の特徴（増加/減少、平均との比較）

含めるチャート:
- 日足
- 4時間足
- 1時間足
- 15分足

#### 7.5 関連銘柄分析

- NQ1! 日足: トレンド、日経との相関
- ES1! 日足: トレンド、NQ との比較（テック vs 全体）
- USD/JPY: トレンド、日経への影響（円安=日経プラス が崩れていないか）
- SOXX: トレンド、半導体の動向、日経テック銘柄への影響

#### 7.6 本日の重要価格水準

- 強いサポート / 中程度サポート / 弱いサポート
- 強いレジスタンス / 中程度レジスタンス / 弱いレジスタンス

#### 7.7 総合判断

- 上昇シナリオ（条件・確率）
- 下降シナリオ（条件・確率）
- レンジシナリオ（条件・確率）
- 全時間軸トレンドの一致・乖離まとめ

#### 7.8 実行可能シナリオ（YAML、機械執行用）※必須・正本

`N225LLMAdvisor/templates/daily_analysis_template.md` の YAML スキーマに従って必ず埋める。

**YAML が本分析の正本となる**。Markdown 部分は人間用の要約。

ルール:
- `scenarios` 配列は A/B/C の 3 件を基本とする
- 各シナリオに `entry.level` / `exits.tp1.price` / `exits.sl.price` を**具体的な数値**で記載
- `probability` は 0.0-1.0 の小数（3 シナリオの合計は 1.0 に近い値）
- `key_levels.resistances` / `supports` は価格と強度（1/2/3）を必ず埋める
- `references.lessons_applied` に、参照した `memory/lessons.md` の ID を列挙（lessons.md が空なら空配列 []）
- `meta.confidence` はこの分析の自信度（0.0-1.0）を客観評価
- `meta.atr_reference` は §5.1 で取得した日足 ATR(20) の値
- `related_markets` セクションを追加し、Tier 2 の現在値も含める
- `event_risk` に §3 で取得した経済指標を入れる

### 8. YAML 検証

出力した YAML ブロックが有効か確認:

1. Python で `yaml.safe_load()` を実行してパース成功を確認
2. 必須キーの存在チェック: `meta.analysis_date`, `scenarios`, `key_levels.resistances`, `key_levels.supports`
3. `scenarios` 配列の長さが 2〜3 件
4. 各シナリオの `probability` が 0.0〜1.0 の範囲

検証失敗時はその場で修正してから保存する。

### 9. 分析結果の保存

- 保存先: `N225LLMAdvisor/analyses/YYYY-MM-DD.md`
- テンプレート: `N225LLMAdvisor/templates/daily_analysis_template.md` を参照

### 10. 休場日処理

§0 で「分析しない日」と判定された場合の処理:

1. `N225LLMAdvisor/analyses/YYYY-MM-DD.md` を作成
2. ヘッダーに「**休場日（理由）**」と記載（例: 「休場日（土曜日）」「休場日（11/23 BCPテスト日）」）
3. ファイル本体は短く、以下のみ記載:
   - 判定理由
   - 翌営業日の予定
   - チャート復元処理に進む
4. §11 へ進む

### 11. チャートを元に戻す

§2 で記録した `default_symbol` と `default_timeframe` に復元:

```
chart_set_symbol(default_symbol)
chart_set_timeframe(default_timeframe)
```

「5分足固定」ではなく**実行前の状態に復元**する。

### 12. TradingView 接続失敗時の挙動

`tv_health_check` がコンパイル失敗・接続失敗したら:

1. リトライ 3 回（10秒間隔）
2. 失敗したら以下のいずれかをユーザーに通知して停止:
   - 「TradingView デバッグモードで起動されているか確認してください」
   - 「Ctrl+Shift+B で TradingView を再起動してください」
3. 部分実行はしない（中途半端な分析ファイルを生成しない）

途中で接続が切れた場合も、すでに取得済みのデータで「部分分析」と明示してファイル保存し、続きは手動で再実行を依頼する。

## 注意事項

- 分析対象日の判定は §0 の「営業日判定」に従う
- 分析はオープン前（9:00 JST 前）を想定
- ファンダメンタル分析は §7.1 の全カテゴリを網羅
- 全時間軸（日足・4H・1H・15M）でのトレンドの一致・乖離を明記
- 関連銘柄（NQ・SP500・USDJPY・SOXX）と日経225の相関を必ず確認
- スクリーンショットは当日フォルダ `screenshots/YYYY-MM-DD/` にまとめる
- memory 群が空でも分析は続行する（蓄積期のため）
- YAML 出力は機械処理の正本。フィールド名を変更しない

## 日次サイクル・学習ループ（運用ルール）

この `/analyze` は日次サイクルの「朝の工程」。完全なサイクル:

```
朝       /analyze 実行（YAML 付きレポート）       → analyses/YYYY-MM-DD.md
 ↓
日中     シナリオ A/B/C を並列監視・トレード実行
 ↓
引け後   結果記録（result_template.md）           → results/YYYY-MM-DD_result.md
 ↓
引け後   振り返り（review_template.md）           → reviews/YYYY-MM-DD_review.md
 ↓
週末     memory/market_memory.md と pattern_accuracy.md を更新
         新しい lessons.md 項目を追加
 ↓
翌朝     /analyze が上記 memory 群を読み込んで再実行
```

**現状の課題**: results/ と reviews/ が空。memory も初版のまま。学習ループが回っていないため、朝分析の精度向上は限定的。引け後ルーティンの再開が望ましい。

**AI の役割**:
- **朝**: 前日までの memory 群と前日 analyses を文脈に取り込み、今日のシナリオ（YAML 含む）を生成
- **連続性**: 毎日が独立ではなく、累積された知識の上に今日を構築する

**ユーザーの役割**:
- 引け後の result.md / review.md 記入（5-15 分）
- 週末の memory 群更新（30 分）
- 月次レビューで方向性判断
