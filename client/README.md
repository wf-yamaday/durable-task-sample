# Durable Task Client

Durable Task orchestration の開始、状態照会、外部イベント送信を担当するクライアントアプリケーションです。

`analyze_reviews` を開始し、instance ID をログに出力したら終了します。完了待ちはしません。状態は DTS、結果は `results/<instance-id>/results.json` で確認できます。

位置引数は読み込む最大行数（既定100、上限1,000）。`--parallelism` は並列バッチ件数（既定5）。`--container`・`--blob` は入力 Blob を指定します。既定は環境変数 `INPUT_CONTAINER=input`・`INPUT_BLOB=Reviews.csv` です。クライアント自体は Blob や OpenAI にはアクセスしません。

## Commands

Azure の Container Apps Job は手動トリガーです。`az containerapp job start` で起動し、自動の定期実行は行いません。既存 Job の切り替えには Bicep の再デプロイが必要です。

```sh
mise run lint
mise run format
mise run start
mise run start -- 100 --parallelism 5 --container input --blob Reviews.csv
docker build -f .docker/Dockerfile -t durable-task-client .
```

ローカル Emulator の `localhost:8080` と `default` タスクハブを既定で利用します。`DTS_ENDPOINT` または `DTS_TASKHUB` で変更できます。
