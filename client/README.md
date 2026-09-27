# Durable Task Client

Durable Task orchestration の開始、状態照会、外部イベント送信を担当するクライアントアプリケーションです。

現時点では `fan_out_average` オーケストレーターを開始し、完了後に乱数一覧と平均を表示します。引数には並列実行する Activity 数を指定でき、省略時は `10` 件です。

## Commands

```sh
mise run lint
mise run format
mise run start
mise run start -- 20
docker build -f .docker/Dockerfile -t durable-task-client .
```

ローカル Emulator の `localhost:8080` と `default` タスクハブを既定で利用します。`DTS_ENDPOINT` または `DTS_TASKHUB` で変更できます。
