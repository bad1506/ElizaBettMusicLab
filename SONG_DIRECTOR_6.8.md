# AI Song Director 6.8 — Audio-to-Song

The Director now receives an audio-derived creative context before generating a song plan.

## Audio-derived context
- BPM and detected beat locations
- half/double tempo alternatives
- estimated key/mode and confidence
- candidate structural boundaries from novelty + energy changes
- section energy and role hints
- full-mix vocal activity windows

## Guardrails
- BPM/key are estimates, not guaranteed truth.
- Section labels are hypotheses, not symbolic arrangement transcription.
- Vocal activity is full-mix pitch activity, not isolated-vocal transcription.
- The Director must distinguish measured facts, inference, and creative proposal.
- It must not copy lyrics, melodies, or distinctive living-artist traits.
