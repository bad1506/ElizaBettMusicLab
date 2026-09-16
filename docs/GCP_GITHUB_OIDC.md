# GitHub → Google Cloud Run deployment

SØNA deploys the backend from GitHub Actions to Cloud Run using GitHub OIDC / Google Cloud Workload Identity Federation. No long-lived Google service-account JSON key is stored in GitHub.

## Target

- Project: `flash-moonlight-484814-e5`
- Region: `europe-west3`
- Artifact Registry repository: `sona`
- Cloud Run service: `sona-api`

## One-time Google Cloud setup

In Google Cloud Console, select project `flash-moonlight-484814-e5`.

### 1. Enable APIs

Enable:

- Artifact Registry API
- Cloud Run Admin API
- IAM Credentials API
- Security Token Service API

Cloud Build is not required by the GitHub Actions deployment path.

### 2. Create an Artifact Registry repository

Create a Docker repository named `sona` in `europe-west3`.

### 3. Create a deployment service account

Create:

`github-cloud-run-deployer@flash-moonlight-484814-e5.iam.gserviceaccount.com`

Grant it only the permissions needed for this deployment:

- Artifact Registry Writer on the `sona` repository
- Cloud Run Admin on the project
- Service Account User on the Cloud Run runtime service identity

The Cloud Run deployment documentation describes the required deployment permissions and recommends user-managed service identities with minimal permissions.

### 4. Create Workload Identity Federation

Create a Workload Identity Pool, for example:

`github-actions`

Create an OIDC provider in that pool with issuer:

`https://token.actions.githubusercontent.com`

Restrict the provider to this repository:

`bad1506/ElizaBettMusicLab`

The recommended trust condition is based on the GitHub repository owner/name and the `main` branch. Do not create an unrestricted provider.

Grant the provider's principal access to impersonate the deployment service account with `roles/iam.workloadIdentityUser`.

The resulting provider resource is used as the GitHub secret `GCP_WORKLOAD_IDENTITY_PROVIDER`.

### 5. Configure GitHub

Repository **Settings → Secrets and variables → Actions**:

Repository variable:

`GCP_PROJECT_ID=flash-moonlight-484814-e5`

Repository secret:

`GCP_WORKLOAD_IDENTITY_PROVIDER=<full provider resource name>`

Repository secret:

`GCP_SERVICE_ACCOUNT=github-cloud-run-deployer@flash-moonlight-484814-e5.iam.gserviceaccount.com`

The workflow also uses the GitHub `production` environment. If environment protection is enabled, configure its approval rules there.

## Runtime secrets

Do not put application secrets in GitHub source or workflow YAML. Store runtime secrets in Google Secret Manager and expose them to Cloud Run as environment variables/secrets.

Required SØNA configuration includes the OpenAI and Telegram credentials and, when using S3/R2 storage:

- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `SONA_STORAGE_PROVIDER=s3`
- `SONA_S3_ENDPOINT`
- `SONA_S3_BUCKET`
- `SONA_S3_REGION`
- `SONA_S3_ACCESS_KEY_ID`
- `SONA_S3_SECRET_ACCESS_KEY`
- `SONA_DATA_DIR=/tmp/sona`

Cloud Run instances have ephemeral local filesystems, so durable user workspace data must use the configured object storage backend.

## Deployment flow

A push to `main` runs:

1. GitHub OIDC authenticates to Google Cloud.
2. Docker builds the SØNA API image.
3. The image is pushed to Artifact Registry.
4. Cloud Run receives the immutable image tagged with the commit SHA.
5. `/health` is called against the deployed service.

This avoids storing a long-lived Google service-account JSON key in GitHub.
