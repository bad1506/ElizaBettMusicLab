---
name: music-lab-testing
description: Validate frontend, backend, API contracts and production-critical flows before release.
---

# Music Lab Testing

- Run the repository CI-equivalent checks before declaring work complete.
- Frontend: `npm run build` and preview smoke test when available.
- Backend: compile all Python modules and validate FastAPI route declarations.
- Test critical paths: songwriter, trends, audio upload, analyzer, mastering and Telegram links.
- When CI fails, inspect the exact failing job logs before making a fix.
- Never hide or dismiss a failing check as unrelated without evidence.
