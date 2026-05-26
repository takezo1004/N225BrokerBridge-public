# トラブルシューティング集

> このドキュメントは `/diagnose` コマンドが参照する主要トラブル事例集です。
> 利用者は **まず `/diagnose` を実行**してください。本文書は症状別の詳細手順リファレンスとして機能します。
>
> ⚠️ **v0.1.0 ドラフト** — テスター環境で内容を順次検証・追記中。

---

## 目次

1. [Webhook が届かない](#1-webhook-が届かない)
2. [kabu API 接続エラー](#2-kabu-api-接続エラー)
3. [Webhook は受信されるが発注されない](#3-webhook-は受信されるが発注されない)
4. [HTTP 400 Invalid Hostname](#4-http-400-invalid-hostname)
5. [起動時例外 / アプリが起動しない](#5-起動時例外--アプリが起動しない)
6. [kabu が「銘柄が見つからない」(Code=4002001) で拒否する](#6-kabu-が銘柄が見つからない-code4002001-で拒否する)
7. [その他の症状](#7-その他の症状)

---

## 1. Webhook が届かない

### 症状

- TradingView の戦略アラートが発火しても、ブリッジが受信しない
- ブリッジのログに `Received` 行が出ない
- TradingView 側のアラート履歴には「送信済」と表示されている

### 主な原因 (確率順)

| 順位 | 原因 | 確認方法 |
|---|---|---|
| 1 | Cloudflare Tunnel (cloudflared) 停止 | `Get-Process cloudflared` |
| 2 | ブリッジが Listen していない | `Get-NetTCPConnection -LocalPort 8001` |
| 3 | Cloudflare 側のセキュリティ設定で `/webhook` パスをブロック | Cloudflare ダッシュボード確認 |
| 4 | TradingView の Webhook URL が間違っている | アラート設定画面の Notifications タブ |
| 5 | passphrase 不一致 | ブリッジログに `Unauthorized` が出る (届いてはいる) |

### 確認手順

#### Step 1: cloudflared が起動しているか
```powershell
Get-Process cloudflared -ErrorAction SilentlyContinue
```
出力がなければ起動:
```powershell
Start-Process "C:\Program Files (x86)\cloudflared\cloudflared.exe" `
    -ArgumentList "tunnel", "--config", "C:\SPB_DATA\.cloudflared\config.yml", "run" `
    -WindowStyle Hidden
```

#### Step 2: ブリッジが 8001 Listen しているか
```powershell
Get-NetTCPConnection -LocalPort 8001 -State Listen
```
出力がなければ、ブリッジ UI 再起動を試す。

#### Step 3: ローカルへ直接 POST してブリッジが受信するか
```powershell
$body = @{
    alert_name = "TestSignal"; interval = 5; trade_type = "new"
    side = "buy"; price = 0; passphrase = "<your_passphrase>"
} | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:8001/webhook/" -Method Post `
    -Body $body -ContentType "application/json"
```
HTTP 200 + Body が返れば**ブリッジ自体は正常**。問題は Cloudflare 経路。

#### Step 4: Cloudflare 経由で疎通テスト
```powershell
Invoke-WebRequest -Uri "https://webhook.your-domain.com/webhook/" -Method Post `
    -Body $body -ContentType "application/json"
```
ここで失敗するなら Cloudflare 側の問題。`webhook.your-domain.com` の DNS / Tunnel ingress / Bypass ルールを確認。

### Bypass ルール (Cloudflare WAF)

`/webhook` パスを全セキュリティから除外するカスタムルールが必要 (TradingView の UA は通常 WAF にひっかかる):

```
Rule name: TV Webhook Bypass
Expression: (http.host eq "webhook.your-domain.com" and http.request.uri.path matches "^/webhook")
Action: Skip (all WAF features)
```

詳細は [N225 メモリ `reference_cloudflare_webhook_bypass.md`](../../memory/reference_cloudflare_webhook_bypass.md) (著者向け補足) 参照。

---

## 2. kabu API 接続エラー

### 症状

- ブリッジ起動時にステータスバーが「ブローカー: 切断」と表示
- ログに `KabuApiError` `TokenAcquisitionFailed` `Unauthorized` 等

### 主な原因

| 順位 | 原因 | 対処 |
|---|---|---|
| 1 | kabu Station 未起動 | kabu Station を起動 (デスクトップショートカット) |
| 2 | kabu Station の API 設定無効 | kabu Station GUI → 設定 → 「API 設定」タブ → API 利用を有効化 |
| 3 | 本番/検証モード不一致 | appsettings.Local.json の `Kabu.Mode` と kabu Station GUI のモード切替を一致させる |
| 4 | API パスワード不一致 | UI 設定画面から再入力 |
| 5 | Token 期限切れ (8 時間) | ブリッジを再起動 (起動時に再取得) |

### 確認手順

#### Step 1: kabu Station 起動確認
```powershell
Get-Process kabusapi -ErrorAction SilentlyContinue
```

#### Step 2: モード確認
```powershell
$config = Get-Content "$env:LOCALAPPDATA\N225BrokerBridge\appsettings.Local.json" | ConvertFrom-Json
$config.Kabu.Mode  # "Production" or "Verification"
```
ブリッジのモード = kabu Station GUI のモード が一致していること。

#### Step 3: Token 取得テスト
```powershell
$port = if ($config.Kabu.Mode -eq "Production") { 18080 } else { 18081 }
$body = @{ APIPassword = "<api_password>" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:$port/kabusapi/token" `
    -Method Post -Body $body -ContentType "application/json"
```
`Token` が返らない場合、kabu Station 側の API 設定 or パスワードを再確認。

### 注意点

- **本番/検証のパスワードは別物**: kabu Station GUI 側でそれぞれ独立に設定
- **Token は約 8 時間で期限切れ**: ブリッジは自動再取得するが、長時間放置すると一時的に失敗するシーンあり
- **kabu Station 起動直後 30 秒は API 不安定**: 起動完了を待ってからブリッジを動かす

---

## 3. Webhook は受信されるが発注されない

### 症状

- ブリッジログに `Received TradingViewSignal` の行は出る
- でも kabu に発注リクエストが飛んでいない (kabu Station の注文一覧に出てこない)

### 主な原因 (確率順)

| 順位 | 原因 | ログメッセージ例 |
|---|---|---|
| 1 | **自動売買トグルが OFF** | `Ignored_AutoTradeDisabled` |
| 2 | 戦略が未登録 (戦略管理画面に追加していない) | `Ignored_unknown_strategy: <name>` |
| 3 | 戦略の `IsEnabled` チェックが OFF | `Ignored_strategy_disabled: <name>` |
| 4 | passphrase 不一致 | `Unauthorized` (HTTP 401) |
| 5 | kabu 接続エラー | `KabuApiError` / `OrderDispatchFailed` |
| 6 | 残高不足・取引時間外などの kabu 側拒否 | `OrderRejected: <kabu のエラーコード>` |

### 確認手順

#### Step 1: ブリッジ UI のステータスバーで自動売買トグルを確認
**最頻原因**。トグルが灰色 (OFF) なら ON に切り替え。

#### Step 2: 戦略管理画面で戦略を確認
ファイル → 戦略 → 戦略管理 で:
- 受信した `alert_name` と一致する戦略が登録済か?
- その戦略の `有効` チェックが ON か?

未登録なら、戦略管理画面の「追加」から登録。

#### Step 3: 直近ログのフィルタ
```powershell
$logDir = "$env:LOCALAPPDATA\N225BrokerBridge\logs"
$latestLog = Get-ChildItem $logDir -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content $latestLog.FullName | Select-String -Pattern "Received|Ignored|Dispatched|Rejected" | Select-Object -Last 20
```

`Ignored_AutoTradeDisabled` が連続していれば → 自動売買 OFF が確定。

#### Step 4: 戦略の発注テスト (手動発注)
ブリッジ UI 左の「手動発注」パネルから 1 枚買い → 実際に kabu に届くか確認。
- 届く: ブリッジ↔kabu は正常、Webhook 側の問題
- 届かない: kabu 接続問題 → §2 へ

---

## 4. HTTP 400 Invalid Hostname

### 症状

- Cloudflare 経由の Webhook が 400 で返る
- TradingView 側で「Webhook delivery failed: 400」が表示される
- ブリッジ側のログには `Received` が出ない (届く前に Cloudflare で弾かれている)

### 原因

Cloudflare Tunnel の `config.yml` で `httpHostHeader` を設定していない。
ブリッジは `Host: localhost` 以外の HTTP リクエストを受け付けない設定になっているため、
Cloudflare が `Host: webhook.your-domain.com` のまま転送すると 400 を返す。

### 対処

`C:\SPB_DATA\.cloudflared\config.yml` を編集:

```yaml
tunnel: <tunnel-id>
credentials-file: C:\SPB_DATA\.cloudflared\<tunnel-id>.json

ingress:
  - hostname: webhook.your-domain.com
    service: http://localhost:8001
    originRequest:
      httpHostHeader: localhost     # ← この 1 行を必ず追加
  - service: http_status:404
```

編集後、cloudflared プロセスを再起動:
```powershell
Get-Process cloudflared | Stop-Process -Force
Start-Process "cloudflared.exe" -ArgumentList "tunnel", "--config", "C:\SPB_DATA\.cloudflared\config.yml", "run" -WindowStyle Hidden
```

### 補足

これは N225 プロジェクトでも 2026-05-13 に発覚した恒久対処。
詳細は著者向けメモリ [`reference_cloudflare_webhook_bypass.md`](../../memory/reference_cloudflare_webhook_bypass.md) 参照。

---

## 5. 起動時例外 / アプリが起動しない

### 症状

- ダブルクリックしてもブリッジ UI が出てこない
- 「.NET Runtime が見つかりません」ダイアログ
- 起動直後にクラッシュ
- Windows Event Log にアプリ例外

### 主な原因

| 順位 | 原因 | 対処 |
|---|---|---|
| 1 | **.NET 8 Desktop Runtime 未インストール** | https://dotnet.microsoft.com/download/dotnet/8.0 から Desktop Runtime をインストール |
| 2 | `appsettings.Local.json` が壊れている (JSON syntax error) | バックアップ取って再生成 (`/setup` の Step 4) |
| 3 | DPAPI 復号失敗 (別 PC からコピーした設定) | DPAPI はユーザー/PC 固有のため、新 PC では `/setup` 再実行 |
| 4 | ポート 8001 が他プロセスに占有されている | `Get-NetTCPConnection -LocalPort 8001` でプロセス特定 → 停止 or ポート変更 |
| 5 | UI レイアウト永続化ファイルが壊れている (ui-layout.json) | `%LOCALAPPDATA%\N225BrokerBridge\ui-layout.json` を削除 (初期状態で再起動) |

### 確認手順

#### Step 1: .NET Runtime 確認
```powershell
dotnet --list-runtimes
```
`Microsoft.WindowsDesktop.App 8.x.x` が含まれていることを確認。

#### Step 2: 設定ファイルの JSON 妥当性
```powershell
try {
    $config = Get-Content "$env:LOCALAPPDATA\N225BrokerBridge\appsettings.Local.json" -Raw | ConvertFrom-Json
    "✅ JSON valid"
} catch {
    "❌ JSON 不正: $($_.Exception.Message)"
}
```
不正なら旧ファイルをバックアップしてから `/setup` の Step 4 を再実行。

#### Step 3: ポート競合確認
```powershell
$conn = Get-NetTCPConnection -LocalPort 8001 -State Listen -EA SilentlyContinue
if ($conn) {
    Get-Process -Id $conn.OwningProcess
}
```
別プロセスが占有していれば停止 or `appsettings.Local.json` の `Webhook.Port` を別ポート (例: 8002) に変更。

#### Step 4: Windows Event Log
```powershell
Get-EventLog -LogName Application -Source ".NET Runtime" -Newest 5 -EA SilentlyContinue
```
直近のアプリ例外スタックトレースを確認。

---

## 6. kabu が「銘柄が見つからない」(Code=4002001) で拒否する

### 症状

- ブリッジから kabu へ `/sendorder/future` を投げると **HTTP 400** が返ってくる
- レスポンス body に `"Code":4002001, "Message":"銘柄が見つからない"`
- TradingView 側のアラートは正常に届き、ブリッジでは `Signal → NewOrder` までは出ている
- kabu Station の注文一覧には何も乗らない (発注成立していない)

### 主な原因 (確率順)

| 順位 | 原因 | 確認ポイント |
|---|---|---|
| 1 | **ブリッジで選択中の銘柄が未解決** (起動直後の数秒間) | ログに `自動売買対象銘柄が未解決 (起動直後/kabu API 応答待ち) のためシグナルを拒否` が出ているか |
| 2 | kabu Station の銘柄解決自体が失敗 (kabu の API パスワード不一致・kabu Station が落ちている等) | 起動時ログに `銘柄解決失敗` が出ていないか・kabu Station が立ち上がっているか |
| 3 | **旧バージョンのブリッジを使っている** (TradingView ティッカー `NK225M1!` を直接 kabu に投げていた) | 送信 body の `"Symbol"` が文字列ティッカーか、数値の銘柄コードか |

### 確認手順

#### Step 1: ブリッジで「自動売買対象銘柄」が確定しているかログで確認

```powershell
$logDir = "$env:LOCALAPPDATA\N225BrokerBridge\logs"
$latestLog = Get-ChildItem $logDir -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content $latestLog.FullName | Select-String -Pattern "自動売買対象銘柄|銘柄解決" | Select-Object -Last 10
```

期待されるログ:
```
銘柄解決成功: 先物コード=NK225micro (限月=202606) → 銘柄コード=161060023 "日経225マイクロ先物 26/06" 2026年6月限
自動売買対象銘柄: 日経225Micro 2026年6月限 (シンボルコード=161060023)
```

`自動売買対象銘柄: 未確定` のままなら kabu の銘柄解決が失敗している。kabu Station の起動と API パスワードを確認 (§2 参照)。

#### Step 2: 送信 body の `Symbol` フィールドを確認

```powershell
Get-Content $latestLog.FullName | Select-String -Pattern "/sendorder/future 送信 body" | Select-Object -Last 1
```

正常な body (修正版以降):
```
/sendorder/future 送信 body={"Password":"***","Symbol":"161060023","Exchange":24,"TradeType":1,...}
```
- `Symbol` が **数値の銘柄コード** (例: `"161060023"` = 日経225Micro 2026年6月限)
- `Password` は `***` でマスクされている

異常な body (旧バージョン、修正前):
```
/sendorder/future 送信 body={"Password":"...","Symbol":"NK225M1!","Exchange":24,...}
```
- `Symbol` が **TradingView ティッカー文字列** になっている → 旧バージョン。最新版に更新してください。

#### Step 3: ブリッジの銘柄選択 UI を確認

ブリッジ UI の手動発注パネル上部の「銘柄」ドロップダウンが、**意図した銘柄** (Mini / Micro) になっているかを確認。
本ブリッジは「**手動発注パネルで選択中の銘柄 = 自動売買の発注先銘柄**」を兼用しているため、ここを切り替えると自動売買の発注先も同時に切り替わる (architecture.md §3.5 参照)。

### 背景・運用上のルール

- TradingView Webhook の `SymbolTicker` フィールド (`"OSE:NK225M1!"` 等) は **発注時に一切使用しない**
- 発注先銘柄は常に「ブリッジで選択中の銘柄の Resolved Symbol Code (kabu 数値コード)」
- これは利用者が「TV では Mini を見ながら、口座資金の都合で Micro を発注する」運用を許容するための仕様
- 詳細は [architecture.md §3.5 自動売買の銘柄ルーティング](architecture.md#35-自動売買の銘柄ルーティング-tv-ティッカー--kabu-銘柄コード) 参照

---

## 7. その他の症状

該当する症状がなければ、以下を順に試してください:

### A. 全体的に動作が遅い・固まる
- ログ容量肥大化の可能性 → `%LOCALAPPDATA%\N225BrokerBridge\logs\` の古いログを削除
- ui-layout.json の破損 → ファイル削除して再起動

### B. UI 表示が崩れている
- 解像度・DPI 設定が極端 (4K + 150% スケーリング等) → ui-layout.json を削除して初期化
- Wpf.Ui のテーマファイル不整合 → アプリ再インストール

### C. 注文が「キャンセル」される
- kabu 側で「取引時間外」「呼値刻みエラー」「呼出余力不足」等 → kabu Station の注文履歴で詳細確認

### D. それでも解決しない場合

GitHub Issue で報告してください:
- 連絡先: `<TBD - 著者の GitHub or サポートメール>`
- 含めるべき情報:
  - 症状 (具体的に)
  - `/diagnose` の出力
  - 直近のログ (`%LOCALAPPDATA%\N225BrokerBridge\logs\` の最新 1 ファイル)
  - 環境情報 (OS バージョン、.NET バージョン、kabu Station バージョン)

**含めてはいけない情報** (秘密扱い):
- passphrase
- kabu API パスワード
- 約定 ID / 注文 ID (個別取引情報、必要なら伏字)

---

## 関連ドキュメント

- [CLAUDE.md](../CLAUDE.md) — Claude Code 用プロジェクトガイド
- [README.md](../README.md) — 利用者向け概要 (TBD)
- [.claude/commands/setup.md](../.claude/commands/setup.md) — 初期セットアップコマンド
- [.claude/commands/verify.md](../.claude/commands/verify.md) — 動作確認コマンド
- [.claude/commands/diagnose.md](../.claude/commands/diagnose.md) — 自動診断コマンド
- [docs/adapters/kabu.md](adapters/kabu.md) — kabu API 仕様 + ハマりポイント集

---

## バージョン

- v0.1.0 (2026-05-22、初版ドラフト)
