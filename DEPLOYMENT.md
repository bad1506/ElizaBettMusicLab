# Eliza Bett Music Lab — deployment

## Frontend — Vercel
The React/Vite interface is configured for Vercel.

Set these Vercel environment variables for the production deployment:

`VITE_API_URL=https://YOUR-BACKEND-DOMAIN`

`VITE_TELEGRAM_URL=https://t.me/YOUR_BOT_USERNAME`

The current local API fallback is `http://127.0.0.1:8000`.

## Backend — Render
The FastAPI/audio engine is a separate service because it uses local filesystem storage and optional CUDA/Demucs processing. A `render.yaml` is included in the repository for deployment.

Recommended Render settings:

- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn api:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`
- `DEMUCS_DEVICE=cpu` for a CPU deployment
- `CORS_ORIGINS=https://eliza-bett-music-lab.vercel.app`
- `OPENAI_API_KEY=<secret>` for live AI Songwriter and Trend Agent calls
- `OPENAI_MODEL=gpt-5.6` (or another model enabled for the OpenAI project)
- Optional: `OPENAI_TIMEOUT_SECONDS=90`

`OPENAI_API_KEY` must exist only on the backend. Never put it in Vercel frontend variables or commit it to Git. OpenAI documents API keys as secrets that should be loaded server-side. citeturn0search1

After Render gives you the backend URL, put it into Vercel as `VITE_API_URL` and redeploy the frontend.

## Telegram
The website must point to the real bot or Mini App URL through `VITE_TELEGRAM_URL`. Do not leave the placeholder value in production.

The backend Telegram authentication endpoint is `POST /auth/telegram` and validates Telegram Mini App `initData` server-side.

## Verification checklist

1. `GET /health` returns `status=ok`.
2. Render service has `/health` configured as its health check.
3. Frontend production `VITE_API_URL` points to the current Render backend.
4. `POST /songwriter` returns a real OpenAI-generated answer when `OPENAI_API_KEY` is configured; without the key it intentionally falls back to a local draft.
5. `POST /songwriter/trends` returns a web-researched report when the OpenAI key is configured.
6. Audio upload accepts WAV/MP3/FLAC/M4A/OGG and creates the latest analysis context.
7. Mastering and Demucs are executed only after an audio file is uploaded.
8. Telegram Mini App authentication remains server-side; never trust `initDataUnsafe`.

## Important
Do not commit API keys, `.env` files, local audio, model caches, or generated project data.
