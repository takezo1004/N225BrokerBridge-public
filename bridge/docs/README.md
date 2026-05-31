# N225BrokerBridge ドキュメント

このフォルダには、N225BrokerBridge を**動かし・設定し・トラブルを解決する**ために必要なドキュメントを置いています。

> このリポジトリは配布用です。ソースの内部設計ドキュメント（アーキテクチャ・ドメインモデル・クラス設計など）は開発者向けの資産のため含めていません。利用に必要なものだけを厳選しています。

---

## ドキュメント一覧

| ファイル | 目的 |
|---|---|
| [simulator-mode.md](./simulator-mode.md) | `--simulator` 起動の仕様。実弾ゼロで Webhook 受信〜発注〜約定〜建玉計上の全フローを Mock ブローカー上で動かす |
| [webhook-api-spec.md](./webhook-api-spec.md) | Webhook エンドポイントの仕様。TradingView の戦略アラートから送る JSON ペイロードの形式・認証・応答 |
| [demo-mode.md](./demo-mode.md) | `--demo` 起動の仕様（スクリーンショット撮影用。外部に繋がず Webhook も受けない） |
| [troubleshooting.md](./troubleshooting.md) | 症状別のトラブルシューティング手順 |

---

## 使い方の入口

- **まず動かしてみたい** → [simulator-mode.md](./simulator-mode.md)
- **自分の戦略の Webhook を設定したい** → [webhook-api-spec.md](./webhook-api-spec.md)
- **動かない・エラーが出る** → [troubleshooting.md](./troubleshooting.md)

セットアップと起動の手順そのものは、配布物に同梱の runtime（`runtime/` 配下）と連載記事が案内します。
