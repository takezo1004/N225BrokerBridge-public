# N225BrokerBridge-public

日経 225 ミニ先物の自動売買システム配布版。

> ⚠️ **このリポジトリは購読者向け配布物です** (Private)
> 詳細な説明・連載記事は [note ブログ](https://note.com/takezo75) を参照してください。

---

## 構成

```
N225BrokerBridge-public/
├── dashboard/          ← 起動・停止・分析ボタンを集約したダッシュボード (Python)
├── bridge/             ← N225BrokerBridge 本体 (C# / .NET 8 / WPF)
├── analysis/           ← LLM シナリオ駆動の朝分析ツール (Python)
├── .claude/            ← Claude Code 命令書 (セットアップ・トラブル対応)
│   ├── commands/       ← /setup /install /verify /diagnose /analyze 等
│   └── skills/         ← 各種設定支援スキル
├── CLAUDE.md           ← Claude Code が最初に読むガイド
├── README.md           ← このファイル
└── .gitignore          ← secrets / 個人情報の二重ガード
```

---

## クイックスタート

1. このリポジトリを `git clone`
2. Claude Code を起動
3. `/setup` で対話的セットアップ開始

詳細は [`CLAUDE.md`](CLAUDE.md) を参照。

---

## 動作要件

- Windows 10 (1809+) / Windows 11 (x64)
- .NET 8 SDK
- kabu Station (au カブコム証券、API 接続可能プラン)
- Cloudflare アカウント (Tunnel 利用)
- TradingView Pro+ (Webhook 機能)
- Claude Code Pro / Max (推奨)
- Python 3.10+ (dashboard / analysis 用)
- TradingView MCP サーバー (analysis 用、別途 git clone 案内)

---

## ライセンス

Proprietary — 購読者の個人利用のみ。再配布禁止。
詳細は購読者向け利用規約を参照。

---

## バージョン

v0.0.1 (初期作成 — 配布前のドラフト状態)
