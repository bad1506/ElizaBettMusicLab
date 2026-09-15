# Security Policy

## Reporting a vulnerability

Do not publish credentials, tokens, exploit code, or private user data in a public issue.

Report security issues privately to the repository owner through GitHub's private security reporting channel when available. Include the affected endpoint/file, impact, reproduction steps, and a safe remediation suggestion.

## Security baseline

- Production API requests require cryptographically validated Telegram Mini App `initData`.
- Secrets belong in Render/GitHub secret storage, never in source files.
- Audio uploads are type-checked and size-limited server-side.
- API rate limits and security headers are enabled in production.
- Public file-directory mounts are not considered a security boundary; generated files must be served only through authenticated routes.
- API documentation is disabled in production unless explicitly enabled with `ENABLE_API_DOCS=true`.

## Secret response

If a credential is exposed, revoke/rotate it immediately at the provider and remove it from every affected location, including Git history where applicable.
