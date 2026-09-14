---
name: music-lab-backend
description: Maintain the FastAPI backend, API contracts, configuration and safe file handling.
---

# Music Lab Backend

- Preserve FastAPI route contracts and existing frontend compatibility.
- Validate uploaded audio extensions and size before processing.
- Keep secrets in environment variables; never hardcode API keys or tokens.
- Preserve CORS configuration and production origins.
- Use Pydantic defaults safely with `Field(default_factory=...)` for mutable values.
- Keep diagnostic errors useful without exposing secrets.
- Run Python compilation and API contract checks before declaring backend work complete.
