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
