# Eliza Bett Music Lab 11.0 — Song Project Workflow

11.0 turns the production engine into a repeatable project workflow.

- Added `project_manager.py` for project manifest, state and final bundle export.
- Added `/project`, `/project/save`, `/project/export` API routes.
- Added one-click `FINALIZE PROJECT` in Production.
- Final ZIP can contain demo, accepted master, production report, lyrics, Suno prompt and notes.
- Project status is explicit: empty → analyzed → mastered.
- Export is deterministic and local; no remote file service is required.

The project bundle is a delivery container, not a DAW session file. Audio measurements and AI outputs remain evidence/creative assistance and should be independently reviewed before release.
