# Durable Task Client

Durable Task orchestration の開始、状態照会、外部イベント送信を担当するクライアントアプリケーションです。

`calc_average` オーケストレーターを開始し、instance IDをログに出力したら終了します。完了待ちはしないため、実行時間に依存せず定期Jobから起動できます。ワークフローの結果や失敗状態はDTS側で確認してください。引数には並列実行する Activity 数を指定でき、省略時は `10` 件です。

## Commands

```sh
mise run lint
mise run format
mise run start
mise run start -- 20
docker build -f .docker/Dockerfile -t durable-task-client .
```

ローカル Emulator の `localhost:8080` と `default` タスクハブを既定で利用します。`DTS_ENDPOINT` または `DTS_TASKHUB` で変更できます。
