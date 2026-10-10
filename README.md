# Durable Task Sample

Durable Task SDK で client、orchestrator worker、activity worker を分離し、Azure Container Apps 上でのスケーラビリティを調査するモノリポです。

## Structure

| Project | Responsibility |
| --- | --- |
| [`client`](./client) | Orchestration の開始、状態照会、外部イベント送信 |
| [`orchestrator-worker`](./orchestrator-worker) | Orchestrator 関数の実行 |
| [`activity-worker`](./activity-worker) | Activity 関数の実行 |

各プロジェクトは独立した uv プロジェクトです。依存関係はプロジェクトごとの `uv.lock` で個別に管理します。

Azure Container Apps、Durable Task Scheduler、Managed Identity などのリソース定義は [`bicep`](./bicep) にあります。

## Amazon review analysis

[Amazon Fine Food Reviews](https://www.kaggle.com/datasets/snap/amazon-fine-food-reviews) の `Reviews.csv` を Blob に配置し、各行の `Text` を Azure OpenAI で分析します。出力は推定評価（1〜5）、日本語の短い要約、採点理由です。元の `Score` はモデルには渡さず、評価用に保持します。

```text
Client → analyze_reviews
           ├─ load_reviews（Blob の CSV を読む）
           ├─ analyze_review × N（並列バッチで LLM 呼び出し）
           └─ save_results（JSON を Blob に保存）
```

初期値は100行・並列5件、処理上限は1,000行です。結果は `results/<instance-id>/results.json` に保存され、成功・失敗件数、成功分の平均推定評価、元の評価との MAE を含みます。入力エラーや Blob 障害はワークフロー失敗、LLM の API エラーや拒否は行単位の失敗として記録します。

データ準備・デプロイは [`bicep/README.md`](./bicep/README.md#review-data-and-model)、ローカル起動の設定は [`activity-worker/README.md`](./activity-worker/README.md) を参照してください。データセット自体はリポジトリに含めません。

### Tests

```sh
mise run test
```

CSV の引用符・改行・UTF-8 チャンク、モデル入力、行単位の失敗、結果保存、並列バッチと MAE を外部サービスなしで検証します。

## Setup

```sh
mise install
```

## Commands

```sh
# Run lint, type, and formatting checks for all projects.
mise run lint

# Apply formatting to all projects.
mise run format

# Start the Durable Task Scheduler emulator.
mise run dts-emulator:up

# Stop the Durable Task Scheduler emulator.
mise run dts-emulator:down

# Run an individual project.
mise --cd client run lint
mise --cd client run format
mise --cd client run start

mise --cd orchestrator-worker run lint
mise --cd orchestrator-worker run format
mise --cd orchestrator-worker run start

mise --cd activity-worker run lint
mise --cd activity-worker run format
mise --cd activity-worker run start
```

`mise run lint` runs Ruff, ty, and Ruff formatting checks. Use `mise run format` to apply formatting.

`mise run dts-emulator:up` starts the emulator in the background if it is not already running. Use `mise run dts-emulator:down` to stop it. Its dashboard is available at `http://localhost:8082` and its scheduler endpoint is available at `localhost:8080`.

Use `mise run infra:build` to validate the Azure Bicep template. See [`bicep/README.md`](./bicep/README.md) for deployment commands.
