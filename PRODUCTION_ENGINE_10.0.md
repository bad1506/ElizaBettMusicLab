# Eliza Bett Music Lab — Song Production Engine 10.0

10.0 is the orchestration layer connecting the existing evidence-driven audio stack.

## Pipeline

`DEMO → ANALYZE → MAP MUSIC → DIRECT SONG → MASTER → VERIFY`

The engine does not synthesize a finished audio track. It creates a connected production decision/report and runs the existing mastering engine.

## Inputs

- latest uploaded audio
- mastering profile / LUFS target
- optional creative brief
- existing Artist DNA and songwriter memory

## Evidence layers

1. Master analysis and decisions
2. Audio-to-Song BPM/key/section estimates
3. Melody Alignment phrase timing and heuristic syllable budgets
4. Vocal Intelligence
5. Song Director creative proposal
6. Master Engine candidate search and QC

## Output

- connected production plan
- director output
- master result
- QC state
- next actions
- JSON production report saved to `optimizer_output`

## Guardrails

- estimated BPM/key/sections/phrases are labeled as estimates or candidates
- syllable budgets are planning heuristics, not transcription
- Artist DNA is evidence/preferences, not a phrase bank
- trend signals are not automatically copied into the song
- mastering rollback preserves the original when QC rejects candidates
