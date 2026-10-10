# Durable Task Activity Worker

Durable Task のアクティビティ関数を実行するワーカーアプリケーションです。

`load_reviews` は Blob の CSV を読み、`analyze_review` は本文から1〜5の評価・日本語要約・理由を生成し、`save_results` は結果 JSON を Blob に保存します。

## Settings

| Environment variable | Value |
| --- | --- |
| `AZURE_OPENAI_ENDPOINT` | 必須。例: `https://<account>.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-5.6-luna`（デプロイ名） |
| `AZURE_OPENAI_REASONING_EFFORT` | `none`（`low`・`medium`・`high` に変更可） |
| `AZURE_OPENAI_MAX_COMPLETION_TOKENS` | `1024`（推論トークンを含む生成上限） |
| `AZURE_OPENAI_TIMEOUT_SECONDS` | `60`（HTTPリクエストごと） |
| `AZURE_STORAGE_ACCOUNT_URL` | 必須。`https://<account>.blob.core.windows.net/` |
| `AZURE_CLIENT_ID` | Azure 上のユーザー割り当て Managed Identity の client ID。ローカルでは未設定 |

Azure OpenAI と Blob は常に `DefaultAzureCredential` 認証です。Azure 上では Bicep で設定した Managed Identity、ローカルでは `az login` したユーザーなどを使います。`DTS_USE_MANAGED_IDENTITY=false` でも LLM/Blob は Azure 認証を使います。ローカルユーザーにも OpenAI と Blob のデータプレーン権限が必要です。

LLM の429・一時的障害は OpenAI SDK で最大2回リトライし、それでも失敗した行は失敗結果として保存します。API エラー本文は結果に保存しません。Activity は少なくとも1回実行されるため、障害復旧時に LLM の重複呼び出し・追加課金が発生する可能性があります。結果保存は instance ID ごとの同一 Blob を上書きするため再実行可能です。

## Commands

Azure OpenAI v1 Chat Completions API（`/openai/v1/`）を使うため、日付付き `api-version` は不要です。レビュー分析では速度・コストを優先して `reasoning_effort=none` を既定にしています。推論を有効にする場合は生成上限も増やし、精度・レイテンシ・料金を比較してください。

```sh
mise run lint
mise run format
mise run start
docker build -f .docker/Dockerfile -t durable-task-activity-worker .
```

The worker connects to the local emulator at `localhost:8080` and uses the `default` task hub by default. Set `DTS_ENDPOINT` or `DTS_TASKHUB` to override them.

CSV は UTF-8（BOM可）、`Id`・`Text`・`Score` 必須です。引用符内の改行に対応し、指定件数までストリーミング読み込みします。空本文・不正な点数・20,000文字を超える本文は入力エラーとします。
