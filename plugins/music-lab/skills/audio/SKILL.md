---
name: music-lab-audio
description: Analyze, process and debug audio workflows safely, including uploads, stems and mastering inputs.
---

# Music Lab Audio

- Treat WAV, MP3, FLAC, M4A and OGG as supported upload formats unless the API changes.
- Preserve the upload -> analysis -> processing -> output flow.
- Prefer deterministic, inspectable audio processing over opaque transformations.
- Validate file existence and safe paths before processing.
- Keep CPU/GPU selection configurable through environment variables.
- For failures, surface actionable diagnostics and never expose credentials.
