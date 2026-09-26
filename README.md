# Durable Task Sample

Durable Task SDK で client と worker を分離し、Azure Container Apps 上でのスケーラビリティとアクティビティ関数の分離を調査するモノリポです。

## Structure

| Project | Responsibility |
| --- | --- |
| [`client`](./client) | Orchestration の開始、状態照会、外部イベント送信 |
| [`worker`](./worker) | Orchestrator と activity 関数の実行 |

client と worker はそれぞれ独立した uv プロジェクトです。依存関係は `client/uv.lock` と `worker/uv.lock` で個別に管理します。

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

# Run an individual project.
mise --cd client run lint
mise --cd client run format
uv run --directory client durable-task-client

mise --cd worker run lint
mise --cd worker run format
uv run --directory worker durable-task-worker
```

`mise run lint` runs Ruff, ty, and Ruff formatting checks. Use `mise run format` to apply formatting.
