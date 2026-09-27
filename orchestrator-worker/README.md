# Durable Task Orchestrator Worker

Durable Task のオーケストレーターを実行するワーカーアプリケーションです。

`calc_average` オーケストレーターは、指定件数の `generate_random_number` アクティビティを並列実行し、値と平均を返します。アクティビティは activity worker が実行します。

## Commands

```sh
mise run lint
mise run format
mise run start
docker build -f .docker/Dockerfile -t durable-task-orchestrator-worker .
```

The worker connects to the local emulator at `localhost:8080` and uses the `default` task hub by default. Set `DTS_ENDPOINT` or `DTS_TASKHUB` to override them.
