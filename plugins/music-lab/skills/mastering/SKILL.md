---
name: music-lab-mastering
description: Work on adaptive AI mastering, loudness targets, QC and master-engine behavior.
---

# Music Lab Mastering

- Treat mastering as a production workflow: analyze -> generate candidate -> process -> loudness/QC -> select -> finalize -> report.
- Preserve adaptive and safe defaults; do not blindly maximize loudness.
- Keep ceiling and target LUFS explicit in API responses where possible.
- Preserve the current engine versioning and environment controls.
- Do not claim a mastering version is live until the deployed commit is verified.
- Test both successful mastering and missing/invalid input cases.
