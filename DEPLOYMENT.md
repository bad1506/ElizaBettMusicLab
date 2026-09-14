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

After Render gives you the backend URL, put it into Vercel as `VITE_API_URL` and redeploy the frontend.

## Telegram
The website must point to the real bot or Mini App URL through `VITE_TELEGRAM_URL`. Do not leave the placeholder value in production.

## Important
Do not commit API keys, `.env` files, local audio, model caches, or generated project data.
