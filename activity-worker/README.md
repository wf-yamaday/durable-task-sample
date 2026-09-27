# Durable Task Activity Worker

Durable Task のアクティビティ関数を実行するワーカーアプリケーションです。

`generate_random_number` アクティビティは、fan-out/fan-in サンプル用に 1 から 100 の乱数を返します。

## Commands

```sh
mise run lint
mise run format
mise run start
docker build -f .docker/Dockerfile -t durable-task-activity-worker .
```

The worker connects to the local emulator at `localhost:8080` and uses the `default` task hub by default. Set `DTS_ENDPOINT` or `DTS_TASKHUB` to override them.
