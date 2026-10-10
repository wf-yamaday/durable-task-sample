# Durable Task Orchestrator Worker

Durable Task のオーケストレーターを実行するワーカーアプリケーションです。

`analyze_reviews` は CSV 読み込み Activity を呼び、レビュー分析を並列バッチで実行し、集計結果の保存 Activity を呼びます。Blob/LLM 呼び出しは Orchestrator 内では行いません。

入力は `container`・`blob`・`limit`・`parallelism` を持つオブジェクトです。`limit` と `parallelism` は1〜1,000。Blob の読み込み・結果保存は Durable Task の指数バックオフで最大3回試行します。返り値は結果 Blob の container/name と集計指標です。

並列数は **ワークフローごと** の上限であり、複数ワークフローが走れば合計並列数は増えます。Container Apps のスケーラー設定はワーカー内部や全体の LLM 同時呼び出し数を制限するものではありません。

PoC ではレビューと分析結果が実行履歴に残ります。57万件全体を処理する場合は、小分けの入力 Blob や継続実行・サブオーケストレーション等を用いた履歴サイズ対策が必要です。

## Commands

```sh
mise run lint
mise run format
mise run start
docker build -f .docker/Dockerfile -t durable-task-orchestrator-worker .
```

The worker connects to the local emulator at `localhost:8080` and uses the `default` task hub by default. Set `DTS_ENDPOINT` or `DTS_TASKHUB` to override them.
