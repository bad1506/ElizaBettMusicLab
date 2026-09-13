# Eliza Bett Music Lab 6.1

## Audio Intelligence Layer

- Added `audio_timeline.py`.
- Added `GET /timeline?source=original|master|reference`.
- Added waveform peak/RMS envelope visualization.
- Added 3-second segment loudness movement visualization.
- Added clickable loudness blocks for navigation.
- Added level-matched A/B preview using integrated LUFS when available.
- Added Master timeline refresh after successful mastering.
- Kept final loudness and true-peak decisions on the backend/QC path.
- Explicitly labeled the timeline as visualization, not a compliance meter.
- Updated API version to 6.1.0.

## Validation

- Python syntax checks passed for modified backend modules.
- Timeline synthetic-audio test passed.
- Full Vite type/build verification still requires the project's npm dependencies (`npm install`) on the target Windows machine.
