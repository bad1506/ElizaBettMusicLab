# Eliza Bett Music Lab 6.5 — Songwriter Memory + Artist DNA

## New
- Persistent local songwriter memory in `songwriter_data/memory.json`.
- Artist DNA profile in `songwriter_data/artist_dna.json`.
- Songwriter prompts automatically receive Artist DNA and recent saved drafts.
- Save generated drafts directly into memory.
- Rebuild Artist DNA from saved work.
- Recent draft browser and voice profile in the Songwriter UI.
- Anti-repetition instruction: memory is used as preference/evidence, not a phrase bank to copy.
- Trend research remains separate from author memory and must distinguish facts from inference.

## API
- `GET /songwriter/memory`
- `POST /songwriter/memory`
- `POST /songwriter/note`
- `POST /songwriter/dna/rebuild`
- `/songwriter` now uses persistent Artist DNA automatically.

## Design principle
The agent should become more consistent with the author's voice over time without becoming repetitive. Saved drafts are evidence of taste, not text to reproduce.
