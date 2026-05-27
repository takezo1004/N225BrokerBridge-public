# N225BrokerBridge

日経 225 ミニ・マイクロ先物 の  **自動売買ブリッジ本体** (オープンソース版)。

TradingView の戦略シグナルを Webhook で受け取り、au カブコム証券 (kabu Station API) に発注 → 約定追跡 → 建玉管理まで完結する WPF アプリケーション。3 年間の個人開発で実運用に到達した本気のシステムです。

```
TradingView (戦略アラート)
    ↓ Webhook
Cloudflare Tunnel (https://your-domain.com/webhook/)
    ↓
N225BrokerBridge (本リポジトリのコード)
    ↓ HTTP API
kabu Station (証券口座、 localhost:18080)
    ↓
東証 (実発注)
```

---

## ⚠️ このリポジトリ単体では動きません

これは **コード本体だけ** を公開したリポジトリです。実際に動かして取引するには、以下 3 つの要素が必要になります:

1. **このコード** (Public、誰でも閲覧・clone 可)
2. **動かすための装備一式 (runtime)** — Claude Code 用の命令書、対話的セットアップスクリプト、ダッシュボード、設定テンプレ等
3. **構築の手順を解説した note 記事** — 各環境 (kabu / TV / Cloudflare) のセットアップから戦略運用までの全工程

2 のうち**シミュレータランタイム** (第 1〜2 話分) は **Public** で公開していて、第 1 話マガジン購入後すぐに `git clone` できます。**本番運用ランタイム** (第 3〜4 話分) は **Private**、第 3 話購入時に著者から GitHub 招待で解放されます。3 (note 記事) は購読制のマガジンです。コードだけでは「読める」が「動かない」設計です (購読者の Claude Code が runtime を本リポと合体させて動く状態にします)。

---

## 📚 note 連載「日経225 自動売買システムをゼロから作る」

開発の物語 (シーズン 1・無料) と装備配布 (シーズン 2・有料) を順次公開中。

### 🟢 シーズン 1 — 無料・構築編 (公開済)
著者がこのシステムをどう設計・実装したかの物語。本リポジトリのコードはここで紹介されているものです。
**[シーズン 1 を読む →](https://note.com/takezo75/m/m0a4e6e90f9eb)**

### 🔵 シーズン 2 — 有料・実装と運用編 (公開準備中)

| # | 話 | 内容 | 配布物 |
|---|---|---|---|
| 第 1 話 | 装備配布のはじまり | 前提環境の確認 / 新規 PC 環境構築 | (シミュレータ runtime は Public、認証不要で clone 可) |
| 第 2 話 | シミュレータでブリッジを動かす | Mock 起動 + Webhook 7 種テスト | 上記と同じ |
| 第 3 話 | 本物の環境を整える | kabu / TV Plus + OSE / Cloudflare / MCP | 本番 runtime (Private) GitHub 招待 |
| 第 4 話 | 本番接続と運用開始 | 朝のルーティーン / 自動売買 ON | 上記と同じ |

第 1 話購入で**シミュレータ runtime** (Public) の使い方と環境構築の知識を入手します。リポ自体は Public なのでクローンに招待不要、kabu 口座も TradingView Plus もまだ無くても、Mock ブローカーでブリッジが動くところまで体験できます。

第 3 話購入で「**本番 runtime**」(Private) リポへ招待されます。本気で実運用したい方向け。

**[シーズン 2 マガジンを見る →](https://note.com/takezo75)** (公開時に更新)

---

## 🏗 このリポジトリに含まれるもの

```
N225BrokerBridge-public/
├── README.md                ← このファイル
└── bridge/
    ├── src/                 ← Bridge ソース (C# / .NET 8 / WPF)
    │   ├── N225BrokerBridge.Domain/         # ドメイン層 (DDD 集約)
    │   ├── N225BrokerBridge.Application/    # ユースケース層
    │   ├── N225BrokerBridge.Infrastructure/ # kabu / Webhook / Mock 実装
    │   └── N225BrokerBridge.UI/             # WPF プレゼンテーション層
    ├── tests/               ← ユニットテスト (180+ ケース)
    ├── installer/           ← Inno Setup インストーラー定義
    ├── docs/                ← 設計ドキュメント 17 ファイル (要件 / 設計 / 運用)
    │   └── README.md        ← 設計ドキュメント索引から読み始めてください
    └── N225BrokerBridge.sln
```

含まれないもの (Private runtime にあり、note マガジン購入で入手):
- Claude Code 用の `CLAUDE.md` (購読者向け命令書)
- `.claude/commands/` (`/setup` `/verify` `/diagnose` `/analyze` 等)
- `.claude/skills/` (kabu / TV / Cloudflare 設定支援スキル)
- 2 つのダッシュボード (シミュレータ用 + 本番モニタリング用)
- Webhook テストペイロード 7 種
- N225 MCP サーバー (TradingView 操作の中核)
- 朝の市場分析ツール (LLM 駆動)

---

## 🎯 主な特徴

- **3 年間の個人開発で実運用到達** — 過去 4 年分の OHLC を使ったバックテスト + ペーパートレード + 本番運用フェーズを経て完成
- **DDD 4 層アーキテクチャ** — 集約・値オブジェクト・ドメインイベントを明示化、180+ テストケース
- **マルチブローカー設計** — `IBrokerAdapter` 抽象で kabu / 楽天 / Mock を差し替え可能 (現状 kabu + Mock 実装)
- **Mock ブローカー内蔵** — `--simulator` 起動で kabu Station 不要、Webhook 受信 → 約定 → 建玉計上の全フローを試せる
- **跨ぎ消化対応** — 複数建玉から部分返済する自動取引の最適化アルゴリズム (`PositionMatcher`)
- **DPAPI 暗号化** — kabu パスワード / Webhook パスフレーズは Windows 標準の DPAPI で暗号化保存
- **3 通りの注文タイプ** — 成行 / 指値 / 逆指値 + FAK/FAS/FOK の TimeInForce 制御
- **詳細な設計ドキュメント** — 要件定義 → ドメインモデル → クラス設計 → シーケンス図 → 状態遷移図まで `bridge/docs/` 配下に揃えている

---

## 🔬 設計を読みたい方へ

コードだけ眺めても面白くないので、**設計ドキュメントを読むのが本リポの楽しみ方** です:

- [bridge/docs/README.md](bridge/docs/README.md) — 設計ドキュメント索引 (ここから読み始める)
- [bridge/docs/architecture.md](bridge/docs/architecture.md) — DDD 4 層構造の全体像
- [bridge/docs/domain-model.md](bridge/docs/domain-model.md) — Order / Position 集約の詳細設計
- [bridge/docs/sequence-diagrams.md](bridge/docs/sequence-diagrams.md) — 13 シナリオのシーケンス図
- [bridge/docs/adapters/kabu.md](bridge/docs/adapters/kabu.md) — kabu API 実装の落とし穴 8 件 (BID/ASK 命名が逆 等)
- [bridge/docs/simulator-mode.md](bridge/docs/simulator-mode.md) — `--simulator` モード仕様

---

## 🛠 動作要件 (実運用時)

| 項目 | 必須 |
|---|---|
| Windows 10 (1809+) / Windows 11 (x64) | ✅ |
| .NET 8 SDK + Desktop Runtime | ✅ |
| Claude Code (Pro / Max) | ✅ (runtime の中核) |
| au カブコム証券 口座 + kabu Station API 接続権 | 本番運用に必須 |
| TradingView Plus プラン以上 + OSE データ追加購読 (Webhook 機能) | 本番運用に必須 |
| Cloudflare アカウント + 独自ドメイン | 本番運用に必須 |
| Python 3.10+ | dashboard / analysis 用 |

**シミュレータモード (`--simulator`) なら kabu / TV / Cloudflare は不要** — 全部のフローを Mock で動かせます (第 1〜2 話の世界)。

---

## 📝 ライセンス

本リポジトリのコードは **閲覧および学習用** に公開しています。実運用での再配布・転売は禁止です。詳細は購読者向け利用規約 (note マガジン購入時に提示) を参照してください。

---

## 🔗 関連リンク

- **note 連載**: https://note.com/takezo75
- **シーズン 1 マガジン (無料・物語編)**: https://note.com/takezo75/m/m0a4e6e90f9eb
- **シーズン 2 マガジン (有料・装備編、公開準備中)**: 近日公開
- **Bridge 設計ドキュメント**: [bridge/docs/README.md](bridge/docs/README.md)

---

## 📦 バージョン

- v0.2.0 (2026-05-27) — 3 リポ構造 (public + runtime-simulator + runtime-production) に再編
- 過去バージョン履歴は [git log](https://github.com/takezo1004/N225BrokerBridge-public/commits/main) を参照

---

> *「コードだけ手にしても、動かなければ意味がない。だから動かす方法ごと渡す」*
> ── 著者 takezo75
