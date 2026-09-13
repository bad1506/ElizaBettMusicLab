# Eliza Bett Music Lab 6.3 — Intelligent Mastering Brain

## Core change
The system now separates **observation → decision → DSP → validation**.

### Added
- `master_brain.py` explainable mastering decision layer.
- Conservative confidence and risk gates.
- Explicit distinction between actionable DSP decisions and observational findings.
- Machine-readable reasons/evidence for each correction.
- Final intelligence validation comparing original and master.
- Engine/API version 6.3.

### Safety rule
Audio Intelligence findings do not automatically become DSP commands. The existing Decision Engine remains the authority for corrective EQ decisions; the Brain adds explanation, confidence and safety context.

### Rollback
If no candidate passes QC, the original is preserved as the final master output.
