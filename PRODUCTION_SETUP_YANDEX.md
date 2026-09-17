# Production setup: Render + Yandex Cloud

This deployment shape keeps the application stateless on Render and moves durable state to Yandex Cloud:

- Frontend: existing Vercel deployment.
- Backend: Render Docker Web Service.
- User files/audio: Yandex Object Storage through the existing S3-compatible storage layer.
- Accounts/sessions/activity: Yandex Managed Service for YDB Serverless.
- AI: configured provider through environment variables.

Render's free filesystem is ephemeral, so SQLite must not be used as the production account database. The application therefore uses `SONA_DB_PROVIDER=ydb` in production. Render documents that free services lose local files on restart/redeploy/spin-down. YDB Serverless has a monthly free package for the first 1,000,000 request units and first 1 GB of storage; Object Storage and Serverless Containers also have free tiers, after which normal usage pricing applies.

## 1. Create Yandex Object Storage

Create a private bucket for application data. Do not make the bucket public.

Required application values:

```text
SONA_STORAGE_PROVIDER=s3
SONA_S3_ENDPOINT=https://storage.yandexcloud.net
SONA_S3_BUCKET=<bucket-name>
SONA_S3_REGION=ru-central1
SONA_S3_ACCESS_KEY_ID=<service-account-static-key-id>
SONA_S3_SECRET_ACCESS_KEY=<service-account-secret>
SONA_S3_PREFIX=sona
```

Grant the service account only the bucket permissions required by the application (object read/write/delete). Yandex Object Storage exposes an S3-compatible API and supports these object operations.

## 2. Create YDB Serverless

Create a YDB Serverless database and a service account with access to the database.

Set:

```text
SONA_DB_PROVIDER=ydb
YDB_ENDPOINT=grpcs://ydb.serverless.yandexcloud.net:2135
YDB_DATABASE=<full-database-path>
YDB_TABLE_PREFIX=sona
```

For Render, prefer a service-account key file over a short-lived access token:

```text
YDB_SERVICE_ACCOUNT_KEY_FILE_CREDENTIALS=/etc/secrets/ydb-sa.json
```

Upload the JSON key as a Render Secret File named `ydb-sa.json`. Never commit the JSON key to Git.

The YDB adapter creates its required tables automatically on first successful connection.

## 3. Configure Render

Create the Web Service from this repository and use the repository `render.yaml` configuration as the source of the service settings.

Required secrets/values:

```text
YDB_DATABASE
YDB_SERVICE_ACCOUNT_KEY_FILE_CREDENTIALS=/etc/secrets/ydb-sa.json
SONA_S3_BUCKET
SONA_S3_ACCESS_KEY_ID
SONA_S3_SECRET_ACCESS_KEY
OPENAI_API_KEY
CORS_ORIGINS
```

Also upload `ydb-sa.json` under Render Secret Files.

No Render persistent disk is required for application state in this architecture.

## 4. AI cost boundary

The infrastructure can be run with free-tier hosting/storage/database allowances, but GPT API usage is not automatically free. A valid AI provider credential is required for GPT-powered features, and provider usage can incur charges.

The application should enforce product quotas before exposing paid AI calls to users. Subscription billing should be the funding source for those quotas; do not expose an unlimited AI endpoint.

## 5. Verification checklist

Run these checks after configuring secrets, before production traffic:

1. `GET /health` returns 200.
2. Register a new account.
3. Log in and refresh the page; the session remains valid.
4. Add activity; restart the service; activity remains present through YDB.
5. Upload an audio file; verify the object exists in Yandex Object Storage.
6. Restart the service; the user workspace is hydrated from Object Storage.
7. Delete a workspace file; verify the remote object is removed.
8. Call `/sona-chat` with an authenticated session.
9. Invoke an allowed agent/tool.
10. Run mastering/audio processing with a test track.
11. Confirm CORS allows only the production frontend origin.
12. Confirm no credentials, `.env`, audio files, or local database files are committed.

Do not enable public bucket access as a workaround for CORS or downloads; use authenticated application routes or controlled signed access instead.
