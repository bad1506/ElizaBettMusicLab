# Music Hearing Skill

Source methodology adapted from `tigrohvost/music-hearing` (MIT).

## Goal
When a real audio file is available, reason from measurable sound characteristics instead of guessing from title or genre labels.

## Workflow
- Start with loudness, peak/crest, dynamics, spectral balance, tempo estimate and stereo information.
- Add deeper musical evidence when available: key, chroma, rhythm, structure, timbre and a bounded similarity representation.
- Distinguish measured audio facts from model interpretation.
- For comparisons, keep the same analysis window and feature set.
- Feed useful findings into Songwriter, Analyzer and Mastering rather than repeating raw metrics.

## SØNA rule
Use the existing SØNA audio pipeline first. This skill is a reasoning layer, not a license to download or retain third-party audio. Never invent a metric when the audio was not actually analyzed.
