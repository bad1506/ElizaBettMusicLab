---
name: music-lab-deployment
description: Safely verify Vercel frontend and Render backend deployments and environment configuration.
---

# Music Lab Deployment

- Frontend production: Vercel project for `eliza-bett-music-lab`.
- Backend production: Render service `ElizaBettMusicLab-1`.
- Verify the deployed commit, health endpoint and relevant logs before saying production is live.
- Preserve `VITE_API_URL` and Telegram configuration on the frontend.
- Never overwrite secrets blindly. Never ask users to paste API keys into chat.
- Keep deployment changes small and reversible.
