# Eliza Bett Music Lab — deployment

## Frontend
The React/Vite interface is configured for Vercel. Set:

`VITE_API_URL=https://YOUR-BACKEND-DOMAIN`

The current local fallback is `http://127.0.0.1:8000`.

## Backend
The FastAPI/audio engine is a separate service. It uses local filesystem storage
and optional CUDA/Demucs processing, so the production backend should run on a
persistent server/worker rather than relying on the Vercel frontend runtime.

Do not commit API keys, `.env` files, local audio, model caches, or generated
project data.
