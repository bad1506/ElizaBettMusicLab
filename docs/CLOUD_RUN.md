# SØNA on Google Cloud Run

This repository can run the FastAPI backend as a stateless Cloud Run service. Persistent user workspaces are provided by the S3/R2 storage backend; the container filesystem is not treated as durable storage.

## Production shape

- Frontend: existing Vercel deployment
- Backend: Cloud Run `sona-api`
- Region: `europe-west3` (Frankfurt)
- Container: `Dockerfile`
- Image registry: Artifact Registry repository `sona`
- Build/deploy: `cloudbuild.yaml`
- Persistent audio/workspace data: S3/R2
- AI: existing OpenAI provider

## One-time Google Cloud setup

Create or select a Google Cloud project, enable billing, and enable:

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
```

Authenticate locally:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

The deployment config creates the `sona` Artifact Registry repository automatically if it does not exist.

## Deploy

Run from the repository root:

```bash
gcloud builds submit --config=cloudbuild.yaml .
```

The build creates the image and deploys `sona-api` to Cloud Run in Frankfurt with:

- 2 vCPU
- 2 GiB RAM
- request timeout 900 seconds
- concurrency 10
- minimum instances 0
- maximum instances 3

These settings intentionally keep the service at zero instances when idle and leave headroom for the existing audio-processing code.

## Required runtime configuration

Set the same application configuration used by production, without committing secrets to Git:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `TELEGRAM_BOT_TOKEN` if Telegram authentication is enabled
- `CORS_ORIGINS` with the Vercel frontend origin
- `SONA_STORAGE_PROVIDER=s3`
- `SONA_S3_ENDPOINT` (S3/R2 endpoint)
- `SONA_S3_BUCKET`
- `SONA_S3_REGION`
- `SONA_S3_ACCESS_KEY_ID`
- `SONA_S3_SECRET_ACCESS_KEY`
- `SONA_S3_PREFIX=sona`

Prefer Google Secret Manager for secret values and inject them into Cloud Run. Never commit credentials or a populated `.env` file.

For an initial smoke deployment, the storage provider may remain `local`, but that mode is ephemeral on Cloud Run and must not be used for persistent user audio.

## Verification

After deployment, verify:

```bash
gcloud run services describe sona-api --region=europe-west3
curl -fsS https://SERVICE_URL/health
```

Then verify authenticated application flows: login/Telegram auth, SØNA Chat, agent invocation, audio upload, Music Intelligence, mastering/stems, and persistence after a new Cloud Run instance is started.

## Cost guardrail

Cloud Run has a monthly always-free request-based tier, but usage beyond the free tier, networking, Artifact Registry, Cloud Build, and other Google Cloud products can incur charges. Keep `min-instances=0` and `max-instances=3` during the early SØNA stage and review billing before increasing limits.
