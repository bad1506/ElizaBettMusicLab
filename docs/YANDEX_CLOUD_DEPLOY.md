# SØNA deployment on Yandex Cloud

SØNA uses Yandex Serverless Containers as the production HTTP runtime. Docker images are stored in Yandex Container Registry, deployment is performed by GitHub Actions, and runtime secrets are stored in Yandex Lockbox.

## Architecture

```text
GitHub main
  -> GitHub Actions + OIDC
  -> Yandex IAM Workload Identity Federation
  -> Yandex Container Registry
  -> Yandex Serverless Containers (sona-api)
  -> Telegram Mini App / web clients

Runtime secrets
  -> Yandex Lockbox
  -> SØNA Serverless Container revision
```

Yandex Cloud supports GitHub OIDC through Workload Identity Federation, so the deployment does not need a long-lived service-account key in GitHub. The federation should be restricted to this repository and the `main` branch.

## One-time Yandex Cloud setup

Create/select a Yandex Cloud folder for SØNA and ensure the linked billing account is `ACTIVE` or `TRIAL_ACTIVE`.

### 1. Container Registry

Create one Container Registry in the SØNA folder, for example:

```text
sona
```

Save its registry ID as the GitHub repository variable `YC_REGISTRY_ID`.

### 2. Deployment service account

Create a service account used only by GitHub Actions, for example:

```text
sona-github-deploy
```

Grant it the minimum roles required for deployment:

- `container-registry.images.pusher`
- `serverless-containers.editor`
- `iam.serviceAccounts.user`
- `serverless-containers.admin` because the workflow makes the HTTP container public
- `functions.editor` because the current Yandex deployment action requires it when Lockbox secrets are attached
- `lockbox.payloadViewer` on the Lockbox secret used by SØNA

Save its ID as the GitHub repository variable `YC_SA_ID`.

### 3. Runtime service account

Create a separate service account, for example:

```text
sona-runtime
```

Do not reuse the GitHub deployment identity for the running application.

Grant the runtime account:

- `container-registry.images.puller`
- `lockbox.payloadViewer` on the SØNA Lockbox secret
- `kms.keys.encrypterDecrypter` only if the Lockbox secret uses a customer-managed KMS key

Save its ID as `YC_RUNTIME_SA_ID`.

### 4. Workload Identity Federation

Create an OIDC workload identity federation in the same folder.

GitHub issuer:

```text
https://token.actions.githubusercontent.com
```

Acceptable audience:

```text
https://github.com/bad1506
```

JWKS URL:

```text
https://token.actions.githubusercontent.com/.well-known/jwks
```

Link the deployment service account to the federation with this external subject:

```text
repo:bad1506/ElizaBettMusicLab:ref:refs/heads/main
```

This prevents the deployment identity from being used by arbitrary repositories or branches.

### 5. Lockbox

Create one custom Lockbox secret containing these keys:

```text
OPENAI_API_KEY
TELEGRAM_BOT_TOKEN
SONA_S3_ENDPOINT
SONA_S3_BUCKET
SONA_S3_REGION
SONA_S3_ACCESS_KEY_ID
SONA_S3_SECRET_ACCESS_KEY
```

Save the secret ID as the GitHub repository variable:

```text
YC_LOCKBOX_SECRET_ID
```

Do not put the secret values in GitHub repository variables, source code, Dockerfiles, or this document.

### 6. GitHub repository variables

Configure these **repository variables** (not secrets):

```text
YC_SA_ID=<GitHub deployment service-account ID>
YC_FOLDER_ID=<SØNA folder ID>
YC_REGISTRY_ID=<Container Registry ID>
YC_RUNTIME_SA_ID=<runtime service-account ID>
YC_LOCKBOX_SECRET_ID=<Lockbox secret ID>
```

No Yandex service-account JSON key is required by this workflow. GitHub requests an OIDC token and the Yandex IAM federation exchanges it for a short-lived IAM token.

## Deployment behavior

Every push to `main`:

1. GitHub requests an OIDC token.
2. Yandex Workload Identity Federation exchanges it for an IAM token for `sona-github-deploy`.
3. Docker builds the repository image.
4. The image is pushed to `cr.yandex/<registry>/sona:<commit-sha>`.
5. `yc-actions/yc-sls-container-deploy@v5` creates/updates `sona-api`.
6. The revision uses the immutable commit SHA image.
7. Lockbox values are injected into the revision as environment variables.

The workflow also supports manual execution with `workflow_dispatch`.

## Storage

The application is configured with:

```text
SONA_STORAGE_PROVIDER=s3
SONA_DATA_DIR=/tmp/sona
```

The local filesystem of a Serverless Container is treated as ephemeral. Persistent user data must remain in the configured S3-compatible backend. `/tmp/sona` is only working space for the running instance.

## Security boundaries

- GitHub receives no long-lived Yandex service-account key.
- Deployment and runtime service accounts are separate.
- The federation is restricted to `bad1506/ElizaBettMusicLab` and `main`.
- Application secrets live in Lockbox.
- The public HTTP endpoint exposes only the SØNA application API; authentication and authorization remain application responsibilities.
- The container image is addressed by commit SHA rather than a mutable production tag.

## Official references

- Yandex Workload Identity Federation with GitHub: https://yandex.cloud/en/docs/iam/tutorials/wlif-github-integration
- Yandex Container Registry: https://yandex.cloud/en/docs/container-registry/quickstart/
- Yandex Serverless Containers: https://yandex.cloud/en/docs/serverless-containers/quickstart/container
- Yandex Lockbox secrets in Serverless Containers: https://yandex.cloud/en/docs/lockbox/operations/serverless/containers
- Yandex Serverless Container GitHub Action: https://github.com/marketplace/actions/yc-serverless-container-deploy
